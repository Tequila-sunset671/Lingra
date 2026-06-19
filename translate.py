"""Перевод текста на базе CTranslate2 + NLLB-200.

Использует тот же движок CTranslate2, что и faster-whisper (он уже в проекте),
поэтому добавляется только токенайзер (transformers) и сама модель NLLB,
которая скачивается с Hugging Face и кешируется — а в .app запекается внутрь,
чтобы перевод работал офлайн.

Кросс-платформенно (macOS / Windows / Linux, ARM и x86_64), рассчитано на
скромные машины (≈8 ГБ RAM):
- готовая int8-модель (минимум памяти);
- вычисления на CPU (CTranslate2 сам выбирает бэкенд под платформу);
- модель и токенайзер грузятся лениво и кешируются.
"""

from __future__ import annotations

import functools
import os
import re
from typing import Iterable, Optional

# Токенайзер NLLB нужен только как токенайзер — фреймворк (torch/tf) не требуется.
# Глушим связанные с этим предупреждения transformers до его импорта.
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import ctranslate2
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

# Готовая CT2-модель int8 — конвертация официальной facebook/nllb-200-distilled-1.3B
# командой OpenNMT (авторы CTranslate2). Скачивается/кешируется как и модель Whisper.
NLLB_REPO = "OpenNMT/nllb-200-distilled-1.3B-ct2-int8"

# Коды языков Whisper / ISO 639-1  ->  коды NLLB (FLORES-200).
# Покрывают и распознаваемые Whisper языки (источник), и доступные для перевода (цель).
LANG_TO_NLLB: dict[str, str] = {
    "ru": "rus_Cyrl",
    "en": "eng_Latn",
    "uk": "ukr_Cyrl",
    "be": "bel_Cyrl",
    "de": "deu_Latn",
    "fr": "fra_Latn",
    "es": "spa_Latn",
    "it": "ita_Latn",
    "pt": "por_Latn",
    "pl": "pol_Latn",
    "nl": "nld_Latn",
    "cs": "ces_Latn",
    "tr": "tur_Latn",
    "ro": "ron_Latn",
    "sv": "swe_Latn",
    "fi": "fin_Latn",
    "el": "ell_Grek",
    "bg": "bul_Cyrl",
    "sr": "srp_Cyrl",
    "ka": "kat_Geor",
    "hy": "hye_Armn",
    "az": "azj_Latn",
    "kk": "kaz_Cyrl",
    "ar": "arb_Arab",
    "he": "heb_Hebr",
    "fa": "pes_Arab",
    "hi": "hin_Deva",
    "zh": "zho_Hans",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "vi": "vie_Latn",
    "th": "tha_Thai",
    "id": "ind_Latn",
}

# Языки, предлагаемые для перевода: код -> название на самом языке (эндоним),
# чтобы не зависеть от языка интерфейса.
TARGET_LANGUAGES: dict[str, str] = {
    "en": "English",
    "uk": "Українська",
    "ru": "Русский",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "pt": "Português",
    "pl": "Polski",
    "tr": "Türkçe",
    "zh": "中文",
    "ja": "日本語",
    "ar": "العربية",
}


class UnsupportedLanguage(ValueError):
    """Язык не поддерживается NLLB (нет в карте FLORES-кодов)."""


def _to_flores(lang: str) -> str:
    code = LANG_TO_NLLB.get(lang)
    if code is None:
        raise UnsupportedLanguage(
            f"Language '{lang}' is not supported for translation. "
            f"Available source codes: {', '.join(sorted(LANG_TO_NLLB))}."
        )
    return code


@functools.lru_cache(maxsize=1)
def _model_dir() -> str:
    """Путь к локальной папке модели.

    snapshot_download уважает HF_HOME / HF_HUB_OFFLINE — то есть внутри .app
    (где HF_HOME указывает в бандл, а HF_HUB_OFFLINE=1) вернёт уже запечённую
    модель без обращения к сети, ровно как у faster-whisper.
    """
    return snapshot_download(NLLB_REPO)


@functools.lru_cache(maxsize=1)
def _translator() -> ctranslate2.Translator:
    return ctranslate2.Translator(_model_dir(), device="cpu", compute_type="int8")


@functools.lru_cache(maxsize=8)
def _tokenizer(src_flores: str):
    # src_lang задаёт префикс исходного языка в токенизации NLLB.
    return AutoTokenizer.from_pretrained(_model_dir(), src_lang=src_flores)


# NLLB обучен на отдельных предложениях и обрезает длинный многосложный ввод,
# поэтому разбиваем текст на предложения и переводим каждое. Граница — знак
# конца предложения (учитываем кириллицу/CJK) + пробел/конец строки.
_SENTENCE_RE = re.compile(r".*?(?:[.!?…。！？]+|$)", re.DOTALL)


def _split_sentences(text: str) -> list[str]:
    parts = [m.group().strip() for m in _SENTENCE_RE.finditer(text)]
    parts = [p for p in parts if p]
    return parts or [text.strip()]


def translate_many(
    texts: Iterable[str],
    source_lang: str,
    target_lang: str,
    *,
    beam_size: int = 4,
) -> list[str]:
    """Переводит список строк с source_lang на target_lang (коды ISO 639-1).

    Пустые строки остаются пустыми; порядок сохраняется. Если языки совпадают —
    строки возвращаются без изменений.
    """
    texts = list(texts)
    if source_lang == target_lang:
        return [t.strip() for t in texts]

    src_flores = _to_flores(source_lang)
    tgt_flores = _to_flores(target_lang)

    # Каждую входную строку режем на предложения; все предложения переводим одним
    # батчем, затем собираем обратно по строкам. owners[k] — индекс исходной строки.
    sentences: list[str] = []
    owners: list[int] = []
    for i, text in enumerate(texts):
        if not text.strip():
            continue
        for sent in _split_sentences(text):
            sentences.append(sent)
            owners.append(i)

    out = [t.strip() for t in texts]
    if not sentences:
        return out

    tokenizer = _tokenizer(src_flores)
    translator = _translator()

    sources = [
        tokenizer.convert_ids_to_tokens(tokenizer.encode(s)) for s in sentences
    ]
    target_prefix = [[tgt_flores]] * len(sources)

    results = translator.translate_batch(
        sources,
        target_prefix=target_prefix,
        beam_size=beam_size,
    )

    # Собираем переведённые предложения обратно в строки.
    grouped: dict[int, list[str]] = {}
    for owner, res in zip(owners, results):
        # hypotheses[0][0] — это сам токен целевого языка, его отбрасываем.
        tokens = res.hypotheses[0][1:]
        translated = tokenizer.decode(tokenizer.convert_tokens_to_ids(tokens)).strip()
        grouped.setdefault(owner, []).append(translated)

    for i, parts in grouped.items():
        out[i] = " ".join(p for p in parts if p).strip()
    return out


def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    *,
    beam_size: int = 4,
) -> str:
    """Переводит цельный текст. Переносы строк сохраняются (каждая строка отдельно)."""
    lines = text.split("\n")
    return "\n".join(translate_many(lines, source_lang, target_lang, beam_size=beam_size))


def is_supported(lang: Optional[str]) -> bool:
    return bool(lang) and lang in LANG_TO_NLLB
