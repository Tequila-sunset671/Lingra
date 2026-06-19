"""Web interface for voice transcription and translation.

Run:
    python app.py
Then open http://127.0.0.1:7860

You can record audio in the browser or upload a file (ogg/opus/mp3/m4a/wav).
PDF documents can be translated on the second tab.

UI language: set APP_LANG=en|uk|ru (otherwise the system locale is used).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import gradio as gr

import core
import i18n
import translate
import translate_pdf

# Языки для дропдаунов: код -> название на самом языке (эндоним).
LANG_CHOICES = [(name, code) for code, name in translate.TARGET_LANGUAGES.items()]
# Для перевода расшифровки: первый пункт — «без перевода».
TRANSLATE_CHOICES = [(i18n.t("translate_none"), "")] + LANG_CHOICES
_AUTO = i18n.t("lang_auto")


def run(audio_path, model_name, language, target_lang):
    if not audio_path:
        return i18n.t("msg_no_audio"), "", "", None, "", ""

    lang = None if language in (None, "", _AUTO) else language
    result = core.transcribe(audio_path, model_name=model_name, language=lang)

    info = i18n.t(
        "info_line",
        lang=result.language,
        prob=result.language_probability,
        dur=core.format_timestamp(result.duration),
        n=len(result.segments),
    )

    timestamped = "\n".join(
        f"[{core.format_timestamp(s.start)}] {s.text.strip()}"
        for s in result.segments
    )

    # Файл субтитров для скачивания (во временную папку — каталог .app только для чтения).
    srt_path = os.path.join(tempfile.gettempdir(), "transcription.srt")
    with open(srt_path, "w", encoding="utf-8") as fh:
        fh.write(core.to_srt(result.segments))

    # --- Перевод (CTranslate2 + NLLB), если выбран целевой язык ---
    translated_text = ""
    translated_ts = ""
    if target_lang:
        if not translate.is_supported(result.language):
            translated_text = i18n.t("msg_src_unsupported", lang=result.language)
        elif result.language == target_lang:
            translated_text = i18n.t("msg_same_lang")
        else:
            try:
                seg_texts = [s.text for s in result.segments]
                translated_segs = translate.translate_many(
                    seg_texts, result.language, target_lang
                )
                translated_text = " ".join(t for t in translated_segs if t).strip()
                translated_ts = "\n".join(
                    f"[{core.format_timestamp(s.start)}] {t}"
                    for s, t in zip(result.segments, translated_segs)
                )
            except Exception as exc:  # модель/токенайзер недоступны и т.п.
                translated_text = i18n.t("msg_translate_failed", error=exc)

    return info, result.text, timestamped, srt_path, translated_text, translated_ts


def run_pdf(pdf_path, source_lang, target_lang, progress=gr.Progress()):
    if not pdf_path:
        return i18n.t("pdf_no_file"), None
    if source_lang == target_lang:
        return i18n.t("pdf_same_lang"), None

    base = Path(pdf_path).stem
    out_path = os.path.join(tempfile.gettempdir(), f"{base}.{target_lang}.pdf")

    def _prog(done, total):
        progress(done / total, desc=i18n.t("pdf_progress", done=done, total=total))

    try:
        translate_pdf.translate_pdf(
            pdf_path, out_path, source_lang, target_lang, progress=_prog
        )
    except Exception as exc:
        return i18n.t("pdf_failed", error=exc), None

    return i18n.t("pdf_done", src=source_lang, tgt=target_lang), out_path


with gr.Blocks(title=i18n.t("app_title")) as demo:
    gr.Markdown(f"# {i18n.t('app_title')}\n{i18n.t('app_subtitle')}")

    with gr.Tab(i18n.t("tab_transcribe")):
        with gr.Row():
            with gr.Column(scale=1):
                audio = gr.Audio(
                    sources=["upload", "microphone"],
                    type="filepath",
                    label=i18n.t("audio_label"),
                )
                model = gr.Dropdown(
                    choices=core.MODELS,
                    value=core.DEFAULT_MODEL,
                    label=i18n.t("model_label"),
                    info=i18n.t("model_info"),
                )
                language = gr.Dropdown(
                    choices=[_AUTO, "ru", "en", "uk", "de", "fr", "es", "it"],
                    value=_AUTO,
                    label=i18n.t("lang_label"),
                )
                target = gr.Dropdown(
                    choices=TRANSLATE_CHOICES,
                    value="",
                    label=i18n.t("translate_to_label"),
                    info=i18n.t("translate_to_info"),
                )
                btn = gr.Button(i18n.t("transcribe_btn"), variant="primary")

            with gr.Column(scale=2):
                info = gr.Markdown()
                text = gr.Textbox(label=i18n.t("text_label"), lines=8)
                timestamps = gr.Textbox(label=i18n.t("timestamps_label"), lines=8)
                srt_file = gr.File(label=i18n.t("srt_label"))
                translated = gr.Textbox(label=i18n.t("translated_label"), lines=8)
                translated_ts = gr.Textbox(label=i18n.t("translated_ts_label"), lines=8)

        btn.click(
            run,
            inputs=[audio, model, language, target],
            outputs=[info, text, timestamps, srt_file, translated, translated_ts],
        )

    with gr.Tab(i18n.t("tab_pdf")):
        gr.Markdown(i18n.t("pdf_intro"))
        with gr.Row():
            with gr.Column(scale=1):
                pdf_in = gr.File(label=i18n.t("pdf_file_label"), file_types=[".pdf"], type="filepath")
                pdf_src = gr.Dropdown(choices=LANG_CHOICES, value="en", label=i18n.t("pdf_source_label"))
                pdf_tgt = gr.Dropdown(choices=LANG_CHOICES, value="uk", label=i18n.t("pdf_target_label"))
                pdf_btn = gr.Button(i18n.t("pdf_btn"), variant="primary")
            with gr.Column(scale=1):
                pdf_status = gr.Markdown()
                pdf_out = gr.File(label=i18n.t("pdf_out_label"))

        pdf_btn.click(
            run_pdf,
            inputs=[pdf_in, pdf_src, pdf_tgt],
            outputs=[pdf_status, pdf_out],
        )


if __name__ == "__main__":
    # При запуске из .app переменная выставлена — открываем браузер автоматически.
    open_browser = os.environ.get("TRANSCRIBE_OPEN_BROWSER") == "1"
    demo.launch(inbrowser=open_browser)
