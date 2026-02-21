from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Callable

from backend.config.settings import settings
from backend.core.segment import ProgressInfo, Segment, TranscriptionResult

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[ProgressInfo], None]


class SubtitlePipeline:
    """
    Điều phối toàn bộ pipeline tạo phụ đề:
    1. Trích xuất âm thanh từ video
    2. Phiên âm âm thanh thành văn bản
    3. (Tùy chọn) Dịch văn bản
    4. Tạo tệp phụ đề
    5. (Tùy chọn) Ghi phụ đề vào video
    """

    TOTAL_STEPS_BASE = 3  # trích xuất + phiên âm + tạo phụ đề
    STEP_DIARIZE = 1
    STEP_TRANSLATE = 1
    STEP_BURNIN = 1

    def __init__(
        self,
        input_path: str,
        source_language: str | None = None,
        target_language: str | None = None,
        output_formats: list[str] | None = None,
        burn_in: bool = False,
        enable_diarization: bool = False,
        whisper_model: str = "large-v3-turbo",
        ollama_model: str | None = None,
        subtitle_style: dict | None = None,
        video_preset: str | None = None,
        on_progress: ProgressCallback | None = None,
    ):
        self.input_path = input_path
        self.source_language = source_language
        self.target_language = target_language
        self.output_formats = output_formats or ["srt"]
        self.burn_in = burn_in
        self.enable_diarization = enable_diarization
        self.whisper_model = whisper_model
        self.ollama_model = ollama_model
        self.subtitle_style = subtitle_style
        self.video_preset = video_preset
        self.on_progress = on_progress

        # Tính tổng số bước
        self.total_steps = self.TOTAL_STEPS_BASE
        if enable_diarization:
            self.total_steps += self.STEP_DIARIZE
        if target_language and target_language != source_language:
            self.total_steps += self.STEP_TRANSLATE
        if burn_in:
            self.total_steps += self.STEP_BURNIN

        self._current_step = 0
        self._results: dict = {}

    def _report(self, percent: float, message: str):
        if self.on_progress:
            step_names = ["Extracting audio", "Transcribing", "Diarizing speakers", "Translating", "Generating subtitles", "Burning subtitles"]
            step_name = step_names[min(self._current_step, len(step_names) - 1)]
            self.on_progress(ProgressInfo(
                step=step_name,
                step_number=self._current_step + 1,
                total_steps=self.total_steps,
                progress_percent=percent,
                message=message,
            ))

    def run(self) -> dict:
        """Chạy toàn bộ pipeline. Trả về dict chứa đường dẫn đầu ra và metadata."""
        start_time = time.time()
        input_file = Path(self.input_path)

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        logger.info("Pipeline started: %s", self.input_path)

        # Bước 1: Trích xuất âm thanh
        audio_path = self._step_extract_audio()

        # Bước 2: Phiên âm
        transcription = self._step_transcribe(audio_path)

        # Bước 3: Phân biệt người nói (tùy chọn)
        segments = transcription.segments
        if self.enable_diarization:
            segments = self._step_diarize(audio_path, segments)

        # Bước 4: Dịch (tùy chọn)
        if self.target_language and self.target_language != transcription.language:
            segments = self._step_translate(segments, transcription.language)

        # Bước 5: Tạo tệp phụ đề
        subtitle_paths = self._step_generate_subtitles(segments, input_file.stem)

        # Bước 6: Ghi phụ đề vào video (tùy chọn)
        output_video_path = None
        if self.burn_in and subtitle_paths:
            output_video_path = self._step_burn_in(subtitle_paths[0])

        # Dọn dẹp tệp âm thanh tạm
        try:
            Path(audio_path).unlink(missing_ok=True)
        except OSError:
            pass

        elapsed = time.time() - start_time
        logger.info("Pipeline complete in %.1fs: %s", elapsed, self.input_path)

        return {
            "detected_language": transcription.language,
            "language_confidence": transcription.language_confidence,
            "segment_count": len(segments),
            "duration": transcription.duration,
            "subtitle_paths": subtitle_paths,
            "output_video_path": output_video_path,
            "elapsed_seconds": elapsed,
        }

    def _step_extract_audio(self) -> str:
        from backend.video.ffmpeg_wrapper import extract_audio

        self._current_step = 0
        self._report(0, "Extracting audio from video...")

        def on_ffmpeg_progress(percent, msg):
            # Co giãn theo phạm vi bước: 0-100 của bước hiện tại
            overall = (self._current_step / self.total_steps) * 100 + (percent / self.total_steps)
            self._report(overall, msg)

        audio_path = extract_audio(
            self.input_path,
            on_progress=on_ffmpeg_progress,
        )

        return audio_path

    def _step_transcribe(self, audio_path: str) -> TranscriptionResult:
        from backend.core.transcriber import transcribe

        self._current_step = 1
        self._report(
            (1 / self.total_steps) * 100,
            "Starting transcription...",
        )

        def on_whisper_progress(percent, msg):
            base = (self._current_step / self.total_steps) * 100
            step_range = (1 / self.total_steps) * 100
            overall = base + (percent / 100) * step_range
            self._report(overall, msg)

        result = transcribe(
            audio_path=audio_path,
            model_name=self.whisper_model,
            language=self.source_language,
            on_progress=on_whisper_progress,
        )

        return result

    def _step_diarize(self, audio_path: str, segments: list[Segment]) -> list[Segment]:
        from backend.core.diarizer import assign_speakers_to_segments, diarize_audio

        self._current_step = 2
        self._report(
            (self._current_step / self.total_steps) * 100,
            "Running speaker diarization...",
        )

        def on_diarize_progress(percent, msg):
            base = (self._current_step / self.total_steps) * 100
            step_range = (1 / self.total_steps) * 100
            overall = base + (percent / 100) * step_range
            self._report(overall, msg)

        speaker_turns = diarize_audio(
            audio_path=audio_path,
            on_progress=on_diarize_progress,
        )

        segments = assign_speakers_to_segments(segments, speaker_turns)
        return segments

    def _step_translate(self, segments: list[Segment], source_lang: str) -> list[Segment]:
        from backend.core.translator import translate_segments
        from backend.core.language_detector import LANGUAGE_NAMES

        # Chỉ số bước động: sau phiên âm(1), tùy chọn phân biệt người nói(2)
        self._current_step = 2 + (1 if self.enable_diarization else 0)
        source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
        target_name = LANGUAGE_NAMES.get(self.target_language, self.target_language)

        self._report(
            (self._current_step / self.total_steps) * 100,
            f"Translating: {source_name} -> {target_name}",
        )

        def on_translate_progress(percent, msg):
            base = (self._current_step / self.total_steps) * 100
            step_range = (1 / self.total_steps) * 100
            overall = base + (percent / 100) * step_range
            self._report(overall, msg)

        segments = translate_segments(
            segments=segments,
            source_lang=source_name,
            target_lang=target_name,
            model=self.ollama_model,
            on_progress=on_translate_progress,
        )

        return segments

    def _step_generate_subtitles(self, segments: list[Segment], base_name: str) -> list[str]:
        from backend.core.subtitle_generator import generate_subtitles

        # Chỉ số bước động: cơ sở(2) + phân biệt người nói?(1) + dịch?(1)
        step_idx = 2
        if self.enable_diarization:
            step_idx += 1
        if self.target_language and self.target_language != self.source_language:
            step_idx += 1
        self._current_step = step_idx
        self._report(
            (self._current_step / self.total_steps) * 100,
            "Generating subtitle files...",
        )

        output_dir = Path(settings.SUBTITLE_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)

        subtitle_paths = []
        use_translated = bool(self.target_language)

        for fmt in self.output_formats:
            output_path = str(output_dir / f"{base_name}.{fmt}")
            result_path = generate_subtitles(
                segments=segments,
                output_path=output_path,
                format=fmt,
                style=self.subtitle_style,
                use_translated=use_translated,
                preset_name=self.video_preset,
            )
            subtitle_paths.append(result_path)

        self._report(
            ((self._current_step + 0.9) / self.total_steps) * 100,
            f"Generated {len(subtitle_paths)} subtitle file(s)",
        )

        return subtitle_paths

    def _step_burn_in(self, subtitle_path: str) -> str:
        from backend.video.ffmpeg_wrapper import burn_subtitles

        self._current_step = self.total_steps - 1
        self._report(
            (self._current_step / self.total_steps) * 100,
            "Burning subtitles into video...",
        )

        input_file = Path(self.input_path)
        output_dir = Path(settings.VIDEO_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{input_file.stem}_subbed{input_file.suffix}")

        def on_ffmpeg_progress(percent, msg):
            base = (self._current_step / self.total_steps) * 100
            step_range = (1 / self.total_steps) * 100
            overall = base + (percent / 100) * step_range
            self._report(overall, msg)

        # Lấy cài đặt mã hóa video từ preset
        video_settings = None
        if self.video_preset:
            from backend.video.presets import get_builtin_preset
            preset = get_builtin_preset(self.video_preset)
            if preset:
                video_settings = preset.get("video_settings")

        result_path = burn_subtitles(
            input_video=self.input_path,
            subtitle_file=subtitle_path,
            output_path=output_path,
            video_settings=video_settings,
            on_progress=on_ffmpeg_progress,
        )

        return result_path
