from __future__ import annotations

import logging
import time
from typing import Callable

from backend.core.segment import Segment, TranscriptionResult, Word
from backend.video.hardware_detector import get_whisper_compute_type, get_whisper_device

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]

# Cache model đã tải để tránh tải lại
_model_cache: dict[str, object] = {}


def _get_model(model_name: str):
    """Tải model faster-whisper (có cache)."""
    from faster_whisper import WhisperModel

    cache_key = f"{model_name}_{get_whisper_device()}_{get_whisper_compute_type()}"
    if cache_key not in _model_cache:
        device = get_whisper_device()
        compute_type = get_whisper_compute_type()
        logger.info(
            "Loading Whisper model: %s (device=%s, compute=%s)",
            model_name, device, compute_type,
        )
        _model_cache[cache_key] = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
        logger.info("Whisper model loaded: %s", model_name)
    return _model_cache[cache_key]


def transcribe(
    audio_path: str,
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    on_progress: ProgressCallback | None = None,
    vad_parameters: dict | None = None,
) -> TranscriptionResult:
    """
    Phiên âm tệp âm thanh sử dụng faster-whisper.

    Tham số:
        audio_path: Đường dẫn đến tệp âm thanh (khuyến nghị WAV).
        model_name: Tên model Whisper.
        language: Mã ngôn ngữ ISO nguồn (None = tự động nhận diện).
        on_progress: Callback(phần trăm, thông báo).

    Trả về:
        TranscriptionResult chứa các đoạn và ngôn ngữ được nhận diện.
    """
    model = _get_model(model_name)

    if on_progress:
        on_progress(0, "Starting transcription...")

    start_time = time.time()

    # Chạy phiên âm
    default_vad = dict(
        threshold=0.3,
        min_silence_duration_ms=300,
        min_speech_duration_ms=100,
        speech_pad_ms=300,
    )
    vad_params = vad_parameters or default_vad

    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=vad_params,
    )

    detected_language = info.language
    language_confidence = info.language_probability
    total_duration = info.duration

    logger.info(
        "Detected language: %s (confidence: %.2f), duration: %.1fs",
        detected_language, language_confidence, total_duration,
    )

    if on_progress:
        on_progress(5, f"Language detected: {detected_language} ({language_confidence:.0%})")

    # Thu thập các đoạn với theo dõi tiến trình
    result_segments: list[Segment] = []

    for segment in segments_iter:
        words = []
        if segment.words:
            words = [
                Word(
                    text=w.word.strip(),
                    start=w.start,
                    end=w.end,
                    confidence=w.probability,
                )
                for w in segment.words
            ]

        result_segments.append(
            Segment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
                words=words,
            )
        )

        # Báo cáo tiến trình dựa trên vị trí thời gian
        if on_progress and total_duration > 0:
            percent = min((segment.end / total_duration) * 90 + 5, 95)
            on_progress(
                percent,
                f"Transcribing: {len(result_segments)} segments ({segment.end:.1f}s / {total_duration:.1f}s)",
            )

    elapsed = time.time() - start_time
    logger.info(
        "Transcription complete: %d segments in %.1fs (%.1fx realtime)",
        len(result_segments), elapsed, total_duration / elapsed if elapsed > 0 else 0,
    )

    if on_progress:
        on_progress(100, f"Transcription complete: {len(result_segments)} segments")

    return TranscriptionResult(
        segments=result_segments,
        language=detected_language,
        language_confidence=language_confidence,
        duration=total_duration,
    )
