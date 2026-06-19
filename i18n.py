"""Локализация интерфейса (English / Українська / Русский).

Язык выбирается один раз при старте:
1. переменная окружения APP_LANG (en / uk / ru);
2. иначе — системная локаль;
3. иначе — английский.

Использование:
    import i18n
    i18n.t("transcribe_btn")
"""

from __future__ import annotations

import locale
import os

SUPPORTED = ("en", "uk", "ru")
DEFAULT = "en"

# Человекочитаемые названия языков интерфейса (эндонимы).
UI_LANGUAGE_NAMES = {"en": "English", "uk": "Українська", "ru": "Русский"}

STRINGS: dict[str, dict[str, str]] = {
    # --- Общее / шапка ---
    "app_title": {"en": "🎙️ Lingra", "uk": "🎙️ Lingra", "ru": "🎙️ Lingra"},
    "app_subtitle": {
        "en": "Transcribe and translate locally — nothing leaves your machine.",
        "uk": "Транскрипція та переклад локально — нічого не залишає ваш комп'ютер.",
        "ru": "Транскрибация и перевод локально — ничего не покидает ваш компьютер.",
    },
    # --- Вкладки ---
    "tab_transcribe": {"en": "🎙️ Transcription", "uk": "🎙️ Транскрипція", "ru": "🎙️ Транскрибация"},
    "tab_pdf": {"en": "📄 PDF translation", "uk": "📄 Переклад PDF", "ru": "📄 Перевод PDF"},
    # --- Вкладка транскрипции ---
    "audio_label": {
        "en": "Audio (record or file)",
        "uk": "Аудіо (запис або файл)",
        "ru": "Аудио (запись или файл)",
    },
    "model_label": {"en": "Model", "uk": "Модель", "ru": "Модель"},
    "model_info": {
        "en": "tiny/base — faster, small/medium — more accurate",
        "uk": "tiny/base — швидше, small/medium — точніше",
        "ru": "tiny/base — быстрее, small/medium — точнее",
    },
    "lang_label": {"en": "Language", "uk": "Мова", "ru": "Язык"},
    "lang_auto": {"en": "auto", "uk": "авто", "ru": "авто"},
    "translate_to_label": {"en": "Translate to", "uk": "Перекласти на", "ru": "Перевести на"},
    "translate_to_info": {
        "en": "NLLB-200 (CTranslate2). The first translation will load the model.",
        "uk": "NLLB-200 (CTranslate2). Перший переклад завантажить модель.",
        "ru": "NLLB-200 (CTranslate2). Первый перевод подгрузит модель.",
    },
    "translate_none": {"en": "— no translation —", "uk": "— без перекладу —", "ru": "— без перевода —"},
    "transcribe_btn": {"en": "Transcribe", "uk": "Транскрибувати", "ru": "Транскрибировать"},
    "text_label": {"en": "Text", "uk": "Текст", "ru": "Текст"},
    "timestamps_label": {"en": "With timestamps", "uk": "З таймкодами", "ru": "С таймкодами"},
    "srt_label": {"en": "Download subtitles (.srt)", "uk": "Завантажити субтитри (.srt)", "ru": "Скачать субтитры (.srt)"},
    "translated_label": {"en": "Translation", "uk": "Переклад", "ru": "Перевод"},
    "translated_ts_label": {
        "en": "Translation with timestamps",
        "uk": "Переклад з таймкодами",
        "ru": "Перевод с таймкодами",
    },
    # --- Статусы транскрипции ---
    "info_line": {
        "en": "Language: {lang} ({prob:.0%})  |  Duration: {dur}  |  Segments: {n}",
        "uk": "Мова: {lang} ({prob:.0%})  |  Тривалість: {dur}  |  Сегментів: {n}",
        "ru": "Язык: {lang} ({prob:.0%})  |  Длительность: {dur}  |  Сегментов: {n}",
    },
    "msg_no_audio": {
        "en": "Upload or record audio.",
        "uk": "Завантажте або запишіть аудіо.",
        "ru": "Загрузите или запишите аудио.",
    },
    "msg_src_unsupported": {
        "en": "⚠️ Translation from «{lang}» is not supported yet.",
        "uk": "⚠️ Переклад з мови «{lang}» поки не підтримується.",
        "ru": "⚠️ Перевод с языка «{lang}» пока не поддерживается.",
    },
    "msg_same_lang": {
        "en": "ℹ️ Source language is the same as the target language.",
        "uk": "ℹ️ Мова оригіналу збігається з мовою перекладу.",
        "ru": "ℹ️ Исходный язык совпадает с языком перевода.",
    },
    "msg_translate_failed": {
        "en": "⚠️ Translation failed: {error}",
        "uk": "⚠️ Не вдалося перекласти: {error}",
        "ru": "⚠️ Не удалось перевести: {error}",
    },
    # --- Вкладка PDF ---
    "pdf_intro": {
        "en": "Translate a PDF **preserving its layout** (NLLB-200 on the CTranslate2 engine). "
              "Pick the source and target language.",
        "uk": "Переклад PDF **зі збереженням верстки** (NLLB-200 на рушії CTranslate2). "
              "Оберіть мову оригіналу та мову перекладу.",
        "ru": "Перевод PDF **с сохранением вёрстки** (NLLB-200 на движке CTranslate2). "
              "Выберите язык оригинала и язык перевода.",
    },
    "pdf_file_label": {"en": "PDF document", "uk": "PDF-документ", "ru": "PDF-документ"},
    "pdf_source_label": {"en": "Source language", "uk": "Мова оригіналу", "ru": "Язык оригинала"},
    "pdf_target_label": {"en": "Translate to", "uk": "Перекласти на", "ru": "Перевести на"},
    "pdf_btn": {"en": "Translate PDF", "uk": "Перекласти PDF", "ru": "Перевести PDF"},
    "pdf_out_label": {
        "en": "Download translated PDF",
        "uk": "Завантажити перекладений PDF",
        "ru": "Скачать переведённый PDF",
    },
    "pdf_no_file": {"en": "Upload a PDF file.", "uk": "Завантажте PDF-файл.", "ru": "Загрузите PDF-файл."},
    "pdf_same_lang": {
        "en": "ℹ️ Source language is the same as the target language.",
        "uk": "ℹ️ Мова оригіналу збігається з мовою перекладу.",
        "ru": "ℹ️ Язык оригинала совпадает с языком перевода.",
    },
    "pdf_progress": {"en": "Page {done}/{total}", "uk": "Сторінка {done}/{total}", "ru": "Страница {done}/{total}"},
    "pdf_done": {
        "en": "✅ Done: translated {src} → {tgt}.",
        "uk": "✅ Готово: переклад {src} → {tgt}.",
        "ru": "✅ Готово: перевод {src} → {tgt}.",
    },
    "pdf_failed": {
        "en": "⚠️ Failed to translate PDF: {error}",
        "uk": "⚠️ Не вдалося перекласти PDF: {error}",
        "ru": "⚠️ Не удалось перевести PDF: {error}",
    },
}


# Распознаём и POSIX-коды (uk_UA), и Windows-имена локалей (Ukrainian_Ukraine).
_LOCALE_HINTS = {
    "uk": ("uk", "ukrainian"),
    "ru": ("ru", "russian"),
    "en": ("en", "english"),
}


def _resolve_lang() -> str:
    env = (os.environ.get("APP_LANG") or "").strip().lower()
    if env in SUPPORTED:
        return env

    candidates = []
    for getter in (locale.getlocale, locale.getdefaultlocale):
        try:
            candidates.append(getter()[0] or "")
        except Exception:
            pass
    # Переменные окружения локали (Linux/macOS) — на случай пустых getlocale().
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        candidates.append(os.environ.get(var, ""))

    for raw in candidates:
        name = raw.strip().lower()
        if not name:
            continue
        for code, hints in _LOCALE_HINTS.items():
            # POSIX: "uk_ua", "ru_ru.utf-8"; Windows: "ukrainian_ukraine".
            if any(name.startswith(h) for h in hints):
                return code
    return DEFAULT


LANG = _resolve_lang()


def t(key: str, **kwargs) -> str:
    """Возвращает строку key на текущем языке (с подстановкой {param})."""
    variants = STRINGS.get(key)
    if not variants:
        return key
    text = variants.get(LANG) or variants.get(DEFAULT) or key
    return text.format(**kwargs) if kwargs else text
