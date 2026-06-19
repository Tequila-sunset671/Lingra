#!/usr/bin/env python3
"""Перевод PDF-документов с сохранением вёрстки (PyMuPDF + CTranslate2/NLLB).

Подход: для каждой страницы извлекаются текстовые блоки с их координатами,
текст переводится (модуль translate.py, движок CTranslate2 + NLLB), исходный
текст затирается (redaction), а перевод вписывается в ту же рамку с автоподбором
размера шрифта. Картинки и графика страницы сохраняются.

Шрифт: кросс-платформенно. notos (Noto Sans из пакета pymupdf-fonts) покрывает
латиницу, кириллицу и греческий; для CJK берутся встроенные в PyMuPDF шрифты.
Системные шрифты ОС не требуются — работает одинаково на macOS/Windows/Linux.

CLI:
    python translate_pdf.py doc.pdf --from en --to ru
    python translate_pdf.py doc.pdf -f en -t ru -o doc_ru.pdf
"""

from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path
from typing import Callable, Optional

import pymupdf

import translate

# Встроенные в PyMuPDF CJK-шрифты (поставляются с библиотекой, не зависят от ОС).
_CJK_FONT = {"zh": "china-s", "ja": "japan", "ko": "korea"}


@functools.lru_cache(maxsize=1)
def _default_font() -> str:
    """notos (Noto Sans из pymupdf-fonts) — латиница+кириллица; иначе встроенный helv."""
    try:
        pymupdf.Font("notos")
        return "notos"
    except Exception:
        return "helv"  # только латиница — pymupdf-fonts не установлен


def _font_for(target_lang: str) -> str:
    return _CJK_FONT.get(target_lang, _default_font())


def _fit_textbox(
    page: "pymupdf.Page",
    rect: "pymupdf.Rect",
    text: str,
    *,
    fontname: str,
    color,
    max_size: float,
    align: int = 0,
) -> None:
    """Вписывает text в rect, уменьшая кегль, пока не поместится."""
    size = max(max_size, 6.0)
    while size >= 5.0:
        rc = page.insert_textbox(
            rect, text, fontsize=size, color=color, align=align, fontname=fontname
        )
        if rc >= 0:  # >=0 — поместилось (вернулся остаток высоты)
            return
        size -= 0.5
    # Не помещается даже мелким — вставляем как есть (может слегка обрезаться).
    page.insert_textbox(rect, text, fontsize=5.0, color=color, align=align, fontname=fontname)


def _block_text(block: dict) -> str:
    """Склеивает текст блока: строки через пробел, как абзац."""
    lines = []
    for line in block.get("lines", []):
        spans = "".join(span["text"] for span in line.get("spans", []))
        if spans.strip():
            lines.append(spans.strip())
    return " ".join(lines).strip()


def _block_style(block: dict):
    """Возвращает (max_size, color) по спанам блока."""
    max_size = 0.0
    color_int = 0
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if span["size"] > max_size:
                max_size = span["size"]
            color_int = span.get("color", color_int)
    color = pymupdf.sRGB_to_pdf(color_int) if color_int else (0, 0, 0)
    return (max_size or 11.0), color


def translate_pdf(
    input_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    *,
    progress: Optional[Callable[[int, int], None]] = None,
) -> str:
    """Переводит PDF, сохраняя вёрстку. Возвращает путь к результату.

    source_lang / target_lang — коды ISO 639-1 (en, ru, uk, de...).
    progress(done_pages, total_pages) — необязательный колбэк прогресса.
    """
    if not translate.is_supported(source_lang):
        raise translate.UnsupportedLanguage(f"Source language '{source_lang}' is not supported.")
    if not translate.is_supported(target_lang):
        raise translate.UnsupportedLanguage(f"Target language '{target_lang}' is not supported.")

    fontname = _font_for(target_lang)
    doc = pymupdf.open(input_path)
    # Не затирать картинки при redaction — только текст.
    keep_images = getattr(pymupdf, "PDF_REDACT_IMAGE_NONE", 0)

    total = doc.page_count
    for pno, page in enumerate(doc):
        blocks = page.get_text("dict").get("blocks", [])
        jobs = []  # (rect, max_size, color, original_text)
        for block in blocks:
            if block.get("type") != 0:  # 0 — текст
                continue
            text = _block_text(block)
            if not text:
                continue
            max_size, color = _block_style(block)
            jobs.append((pymupdf.Rect(block["bbox"]), max_size, color, text))

        if not jobs:
            if progress:
                progress(pno + 1, total)
            continue

        # Переводим все блоки страницы одним батчем.
        translations = translate.translate_many(
            [j[3] for j in jobs], source_lang, target_lang
        )

        # 1) Затираем оригинальный текст (картинки сохраняем).
        for rect, *_ in jobs:
            page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions(images=keep_images)

        # 2) Вписываем перевод в те же рамки.
        for (rect, max_size, color, _), translated in zip(jobs, translations):
            if translated.strip():
                _fit_textbox(
                    page, rect, translated,
                    fontname=fontname, color=color, max_size=max_size,
                )

        if progress:
            progress(pno + 1, total)

    # Сабсет шрифтов: встраиваем только используемые глифы, иначе PDF раздувается.
    try:
        doc.subset_fonts(fallback=True)
    except Exception:
        pass  # fontTools может отсутствовать — тогда сохраняем как есть

    doc.save(output_path, deflate=True, garbage=4)
    doc.close()
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Translate a PDF preserving its layout (PyMuPDF + NLLB)."
    )
    parser.add_argument("files", nargs="+", help="PDF files to translate")
    parser.add_argument(
        "-f", "--from", dest="source", required=True, metavar="LANG",
        help="Source language (en, ru, uk, de...).",
    )
    parser.add_argument(
        "-t", "--to", dest="target", required=True, metavar="LANG",
        help="Target language (en, ru, uk, de...).",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output file name (only with a single input). "
             "Default: <name>.<lang>.pdf next to the original.",
    )
    args = parser.parse_args()

    for code, role in ((args.source, "source"), (args.target, "target")):
        if code not in translate.LANG_TO_NLLB:
            print(
                f"⚠️  {role.capitalize()} language '{code}' is not supported. "
                f"Available: {', '.join(sorted(translate.LANG_TO_NLLB))}",
                file=sys.stderr,
            )
            return 2

    if args.output and len(args.files) > 1:
        print("⚠️  -o/--output can only be used with a single file.", file=sys.stderr)
        return 2

    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"⚠️  File not found: {f}", file=sys.stderr)
            continue

        out = Path(args.output) if args.output else path.with_name(
            f"{path.stem}.{args.target}.pdf"
        )
        print(f"📄 {path.name} → translating {args.source}→{args.target} ...", file=sys.stderr)

        def _prog(done, total):
            print(f"   page {done}/{total}", file=sys.stderr)

        translate_pdf(str(path), str(out), args.source, args.target, progress=_prog)
        print(f"   💾 {out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
