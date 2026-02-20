from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Word:
    text: str
    start: float
    end: float
    confidence: float = 0.0


@dataclass
class Segment:
    """A single subtitle segment with timing and text."""

    start: float
    end: float
    text: str
    speaker: str | None = None
    words: list[Word] = field(default_factory=list)
    translated_text: str | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start

    def format_timestamp_srt(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def format_timestamp_vtt(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def to_srt_block(self, index: int) -> str:
        start_ts = self.format_timestamp_srt(self.start)
        end_ts = self.format_timestamp_srt(self.end)
        text = self.translated_text or self.text
        if self.speaker:
            text = f"[{self.speaker}]: {text}"
        return f"{index}\n{start_ts} --> {end_ts}\n{text}\n"


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""

    segments: list[Segment]
    language: str
    language_confidence: float = 0.0
    duration: float = 0.0

    @property
    def text(self) -> str:
        return " ".join(seg.text for seg in self.segments)

    @property
    def segment_count(self) -> int:
        return len(self.segments)


@dataclass
class ProgressInfo:
    """Progress information for pipeline steps."""

    step: str
    step_number: int
    total_steps: int
    progress_percent: float
    message: str
    eta_seconds: float | None = None

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "step_number": self.step_number,
            "total_steps": self.total_steps,
            "progress_percent": round(self.progress_percent, 1),
            "message": self.message,
            "eta_seconds": self.eta_seconds,
        }
