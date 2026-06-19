"""Ядро транскрибации на базе faster-whisper (переписанный Whisper от OpenAI).

Кросс-платформенно (macOS / Windows / Linux, ARM и x86_64). Рассчитано на
скромные машины (например, 8 ГБ RAM):
- вычисления на CPU с int8-квантизацией (минимум памяти, работает везде);
- модель загружается лениво и кешируется, чтобы не грузить её на каждый файл.
"""

from __future__ import annotations

import functools
import warnings
from dataclasses import dataclass
from typing import Iterable, Optional

from faster_whisper import WhisperModel

# Доступные модели — от самой лёгкой к самой точной.
# На 8GB RAM комфортно работают tiny / base / small.
# medium тоже запустится, но будет заметно медленнее и съест больше памяти.
MODELS = ["tiny", "base", "small", "medium"]
DEFAULT_MODEL = "small"

# Безвредные RuntimeWarning из mel-спектрограммы (numpy 2.x на тишине в начале файла).
warnings.filterwarnings("ignore", category=RuntimeWarning, module="faster_whisper")


@functools.lru_cache(maxsize=2)
def load_model(name: str = DEFAULT_MODEL) -> WhisperModel:
    """Загружает (и кеширует) модель Whisper.

    compute_type="int8" даёт минимальное потребление RAM.
    device="cpu" — CTranslate2 сам выбирает оптимизированный CPU-бэкенд под
    платформу (Apple Accelerate на macOS-ARM, oneDNN/MKL на x86_64).
    """
    return WhisperModel(name, device="cpu", compute_type="int8")


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    language: str
    language_probability: float
    duration: float
    segments: list[Segment]

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments).strip()


def transcribe(
    audio_path: str,
    model_name: str = DEFAULT_MODEL,
    language: Optional[str] = None,
) -> TranscriptionResult:
    """Транскрибирует аудиофайл (любой формат, который понимает ffmpeg: ogg/opus/mp3/m4a/wav...).

    language=None — автоопределение языка.
    """
    model = load_model(model_name)

    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True,  # отсекает тишину — быстрее и точнее на голосовых
        beam_size=5,
    )

    segments = [
        Segment(start=s.start, end=s.end, text=s.text)
        for s in segments_iter
    ]

    return TranscriptionResult(
        language=info.language,
        language_probability=info.language_probability,
        duration=info.duration,
        segments=segments,
    )


def format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def to_srt(segments: Iterable[Segment]) -> str:
    """Субтитры в формате SRT."""
    def srt_time(t: float) -> str:
        ms = int((t - int(t)) * 1000)
        m, s = divmod(int(t), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{srt_time(seg.start)} --> {srt_time(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines)
