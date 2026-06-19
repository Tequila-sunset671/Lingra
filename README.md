# 🎙️ Lingra

[![CI](https://github.com/Tequila-sunset671/Lingra/actions/workflows/ci.yml/badge.svg)](https://github.com/Tequila-sunset671/Lingra/actions/workflows/ci.yml)

**Lingra** transcribes voice messages into text and translates text and PDF
documents — all **locally**, nothing is ever sent to the cloud.

- **Transcription** is powered by [OpenAI Whisper](https://github.com/openai/whisper)
  via [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) (CTranslate2).
- **Translation** uses Meta's [NLLB-200](https://ai.meta.com/research/no-language-left-behind/)
  on the same [CTranslate2](https://github.com/OpenNMT/CTranslate2) engine (~200 languages).

Runs on **macOS, Windows and Linux**, on both **Apple Silicon (ARM) and Intel/AMD
(x86_64)**. CPU inference with int8 quantization, tuned for modest machines
(≈ 8 GB RAM) — no GPU required.

## Features

- Web interface (record from the microphone in the browser or upload a file) and a CLI
- Any format via ffmpeg: `ogg/opus` (Telegram, WhatsApp), `mp3`, `m4a`, `wav`...
- Automatic language detection for transcription
- **Text translation** into many languages (NLLB-200)
- **PDF translation** preserving the original layout
- Export to plain text and `.srt` subtitles
- Silence VAD filter — faster and more accurate on voice messages
- UI in **English, Ukrainian and Russian** (`APP_LANG=en|uk|ru`)

## System requirements

| | Minimum | Recommended |
|---|---|---|
| **OS** | macOS 11+, Windows 10/11 (x64), Linux (x86_64/aarch64) | same |
| **CPU** | any 64-bit ARM64 or x86_64, no GPU needed | 4+ cores |
| **RAM** | **4 GB** (Whisper `tiny`/`base`, no translation) | **8 GB+** (Whisper `small` + NLLB translation) |
| **Disk** | ~2.5 GB free (models + dependencies) | ~3 GB |
| **Python** | 3.10+ | 3.11 / 3.12 |

Approximate model download sizes (fetched once, then cached):
Whisper `tiny` ≈ 75 MB · `base` ≈ 145 MB · `small` ≈ 500 MB · `medium` ≈ 1.5 GB;
NLLB-200 distilled-1.3B ≈ 1.4 GB (only if you use translation).

Audio decoding is handled by [PyAV](https://github.com/PyAV-Org/PyAV) (a
dependency of `faster-whisper`), which bundles ffmpeg in its wheels — so **no
separate ffmpeg install is required** on any platform.

> Notes: no GPU is required — everything runs on the CPU with int8 quantization.
> Prebuilt CTranslate2 wheels exist for macOS (arm64/x86), Linux (x86_64/aarch64)
> and Windows (x64); Windows-on-ARM is not currently supported.

## Quick start

Clone the repo, then run the launcher for your OS — it creates a virtual
environment and installs dependencies on first launch:

```bash
# macOS / Linux
./run.sh
```

```bat
REM Windows
run.bat
```

Then open **http://127.0.0.1:7860**.

> On the first run the models are downloaded from Hugging Face and cached
> (Whisper `small` ≈ 500 MB, NLLB-200 distilled-1.3B ≈ 1.4 GB).

### Manual setup

```bash
python3 -m venv .venv
# macOS/Linux:
.venv/bin/pip install -r requirements.txt && .venv/bin/python app.py
# Windows:
.venv\Scripts\pip install -r requirements.txt && .venv\Scripts\python app.py
```

## UI language

Lingra picks the interface language from `APP_LANG`, falling back to your system
locale, then English:

```bash
APP_LANG=uk ./run.sh      # Ukrainian
APP_LANG=en ./run.sh      # English
APP_LANG=ru ./run.sh      # Russian
```

## Translation

### Text

Transcriptions can be translated into another language locally (NLLB-200 on the
CTranslate2 engine).

- **Web:** pick a language in the “Translate to” dropdown to get a translated
  text block (plain and with timestamps).
- **CLI:**

  ```bash
  python transcribe.py voice.ogg --translate-to en
  python transcribe.py *.ogg --output texts/ --translate-to de   # saves *.de.txt
  ```

Text is translated sentence by sentence so NLLB doesn't truncate long lines.

### PDF documents

PDFs are translated **preserving the layout**: text is extracted block by block
([PyMuPDF](https://pymupdf.readthedocs.io/)), translated, and placed back where
the original text was; images and graphics are kept. The source language is set
manually (a PDF carries no language metadata).

- **Web:** the “📄 PDF translation” tab — upload a file, choose the source and
  target language, download the translated PDF.
- **CLI:**

  ```bash
  python translate_pdf.py doc.pdf --from en --to uk          # → doc.uk.pdf
  python translate_pdf.py doc.pdf -f en -t uk -o doc_uk.pdf  # custom name
  ```

> Fonts are bundled via `pymupdf-fonts` (Noto Sans — Latin + Cyrillic) with
> PyMuPDF's built-in CJK fonts, so it works the same on every OS without relying
> on system fonts. Translated text is auto-fitted to the original box; on very
> dense layouts it may shrink slightly. Works with “digital” PDFs (with a text
> layer); scanned PDFs without OCR cannot be translated.

## CLI reference

```bash
# simple transcription
python transcribe.py voice.ogg

# pick model and language
python transcribe.py voice.ogg --model base --language ru

# with timestamps
python transcribe.py voice.ogg --timestamps

# save .txt to a folder + .srt subtitles
python transcribe.py *.ogg --output texts/ --srt

# transcribe and translate to English
python transcribe.py voice.ogg --translate-to en

# translate a PDF (English → Ukrainian)
python translate_pdf.py doc.pdf --from en --to uk
```

## Choosing the Whisper model (for 8 GB RAM)

| Model   | RAM    | Speed        | Quality   |
|---------|--------|--------------|-----------|
| `tiny`  | ~0.5GB | very fast    | low       |
| `base`  | ~0.7GB | fast         | medium    |
| `small` | ~1.5GB | medium       | good ← default |
| `medium`| ~3GB   | slow         | excellent |

`small` is a good balance. Use `base` if RAM is tight or you need speed.

## macOS app bundle (optional)

On macOS you can build a **standalone** `Lingra.app` that runs on double-click
with no Python install and no internet — a portable Python, all libraries and
both models (Whisper + NLLB) are baked in:

```bash
./build_app.sh
```

- Bake a different Whisper model: `BUNDLE_MODEL=base ./build_app.sh`
- Skip baking the translation model (smaller `.app`, downloaded on first use):
  `BUNDLE_NLLB= ./build_app.sh`

## Project layout

- `core.py` — transcription core (model loading, decoding, SRT)
- `translate.py` — text translation (CTranslate2 + NLLB-200)
- `translate_pdf.py` — PDF translation with layout preservation (PyMuPDF) + CLI
- `transcribe.py` — transcription CLI
- `i18n.py` — interface localization (EN/UK/RU)
- `app.py` — web interface (Gradio)
- `run.sh` / `run.bat` — launchers (create the venv on first run)
- `build_app.sh` — builds the macOS `Lingra.app`

## License

[MIT](LICENSE) © Andriy Bezditko
