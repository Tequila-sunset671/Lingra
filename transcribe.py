#!/usr/bin/env python3
"""CLI for transcribing voice messages.

Examples:
    python transcribe.py voice.ogg
    python transcribe.py voice.ogg --model base --language ru
    python transcribe.py voice.ogg --srt              # save subtitles next to audio
    python transcribe.py *.ogg --output texts/        # batch into a folder
    python transcribe.py voice.ogg --translate-to en  # also translate the transcript
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import core
import translate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe voice messages (Whisper / faster-whisper)."
    )
    parser.add_argument("files", nargs="+", help="Audio files (ogg, opus, mp3, m4a, wav...)")
    parser.add_argument(
        "-m", "--model", default=core.DEFAULT_MODEL, choices=core.MODELS,
        help=f"Model size (default: {core.DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-l", "--language", default=None,
        help="Language code (ru, en, ...). Default: auto-detect.",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Folder to save .txt files (if omitted — print to console).",
    )
    parser.add_argument(
        "--srt", action="store_true",
        help="Also save .srt subtitles next to the audio.",
    )
    parser.add_argument(
        "-t", "--timestamps", action="store_true",
        help="Print text with per-segment timestamps.",
    )
    parser.add_argument(
        "--translate-to", default=None, metavar="LANG",
        help="Translate the transcript to LANG (en, ru, uk, de...) via CTranslate2 + NLLB. "
             "Saved/printed in addition to the original.",
    )
    args = parser.parse_args()

    if args.translate_to and args.translate_to not in translate.LANG_TO_NLLB:
        print(
            f"⚠️  Translation language '{args.translate_to}' is not supported. "
            f"Available: {', '.join(sorted(translate.LANG_TO_NLLB))}",
            file=sys.stderr,
        )
        return 2

    out_dir = Path(args.output) if args.output else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading model '{args.model}' (first run downloads it from Hugging Face)...",
          file=sys.stderr)

    for f in args.files:
        path = Path(f)
        if not path.exists():
            print(f"⚠️  File not found: {f}", file=sys.stderr)
            continue

        print(f"\n🎧 {path.name} ...", file=sys.stderr)
        result = core.transcribe(str(path), model_name=args.model, language=args.language)
        print(
            f"   language: {result.language} ({result.language_probability:.0%}), "
            f"duration: {core.format_timestamp(result.duration)}",
            file=sys.stderr,
        )

        if args.timestamps:
            body = "\n".join(
                f"[{core.format_timestamp(s.start)}] {s.text.strip()}"
                for s in result.segments
            )
        else:
            body = result.text

        if out_dir:
            txt_path = out_dir / f"{path.stem}.txt"
            txt_path.write_text(body + "\n", encoding="utf-8")
            print(f"   💾 {txt_path}", file=sys.stderr)
        else:
            print(body)

        # --- Translation (CTranslate2 + NLLB) ---
        if args.translate_to:
            if not translate.is_supported(result.language):
                print(
                    f"   ⚠️  Translation from '{result.language}' is not supported — skipping.",
                    file=sys.stderr,
                )
            elif result.language == args.translate_to:
                print("   ℹ️  Source language equals target language — skipping.",
                      file=sys.stderr)
            else:
                print(f"   🌐 Translating to '{args.translate_to}'...", file=sys.stderr)
                seg_texts = [s.text for s in result.segments]
                translated_segs = translate.translate_many(
                    seg_texts, result.language, args.translate_to
                )
                if args.timestamps:
                    tbody = "\n".join(
                        f"[{core.format_timestamp(s.start)}] {t}"
                        for s, t in zip(result.segments, translated_segs)
                    )
                else:
                    tbody = " ".join(t for t in translated_segs if t).strip()

                if out_dir:
                    tpath = out_dir / f"{path.stem}.{args.translate_to}.txt"
                    tpath.write_text(tbody + "\n", encoding="utf-8")
                    print(f"   💾 {tpath}", file=sys.stderr)
                else:
                    print(f"\n--- Translation ({args.translate_to}) ---")
                    print(tbody)

        if args.srt:
            srt_path = (out_dir or path.parent) / f"{path.stem}.srt"
            srt_path.write_text(core.to_srt(result.segments), encoding="utf-8")
            print(f"   💾 {srt_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
