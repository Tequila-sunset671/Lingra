"""Cross-platform smoke test for CI.

Verifies that everything installs and imports on the target OS/arch and that the
PDF font works — WITHOUT downloading any model (so it stays fast and offline).
Run: python tests/smoke_test.py
"""

import os
import sys

# Запускаемся из корня репозитория.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1) Весь граф зависимостей импортируется (gradio, faster-whisper -> ctranslate2,
#    transformers, pymupdf, av). Импорт app строит Gradio Blocks, но не запускает сервер.
import app          # noqa: E402,F401
import core         # noqa: E402,F401
import i18n         # noqa: E402
import translate    # noqa: E402,F401
import translate_pdf  # noqa: E402
print("[1/4] imports OK")

# 2) В i18n у каждого ключа есть все поддерживаемые языки.
missing = [
    (key, lang)
    for key, variants in i18n.STRINGS.items()
    for lang in i18n.SUPPORTED
    if lang not in variants
]
assert not missing, f"missing i18n translations: {missing}"
print(f"[2/4] i18n OK: {len(i18n.STRINGS)} keys x {i18n.SUPPORTED}")

# 3) Кросс-платформенный шрифт для PDF: рендер кириллицы + сабсет (без системных шрифтов).
import pymupdf  # noqa: E402

doc = pymupdf.open()
page = doc.new_page()
rc = page.insert_textbox(
    pymupdf.Rect(40, 40, 520, 120),
    "Привіт, світ! Ґ ї є — Hello world.",
    fontname=translate_pdf._font_for("uk"),
    fontsize=16,
)
assert rc >= 0, "translated text did not fit the box"
doc.subset_fonts(fallback=True)
doc.close()
print("[3/4] PDF font OK")

# 4) Нативный движок CTranslate2 загружен.
import ctranslate2  # noqa: E402

print(f"[4/4] ctranslate2 {ctranslate2.__version__} OK")
print("SMOKE TEST PASSED")
