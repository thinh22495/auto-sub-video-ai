from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from backend.config.settings import settings
from backend.video.hardware_detector import get_ffmpeg_decoder, get_ffmpeg_encoder

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]  # (percent, message)


def extract_audio(
    input_path: str,
    output_path: str | None = None,
    sample_rate: int = 16000,
    on_progress: ProgressCallback | None = None,
) -> str:
    """Trích xuất âm thanh từ video thành WAV mono 16kHz cho Whisper."""
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        temp_dir = Path(settings.TEMP_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(temp_dir / f"{input_file.stem}_audio.wav")

    duration = get_duration(input_path)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i", input_path,
        "-vn",                          # no video
        "-acodec", "pcm_s16le",         # 16-bit PCM
        "-ar", str(sample_rate),        # sample rate
        "-ac", "1",                     # mono
    ]

    use_progress = on_progress is not None and duration > 0
    if use_progress:
        cmd.extend(["-progress", "pipe:1"])

    cmd.append(output_path)

    logger.info("Đang trích xuất âm thanh: %s -> %s", input_path, output_path)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE if use_progress else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if use_progress and process.stdout:
        _parse_ffmpeg_progress(process.stdout, duration, on_progress, "Extracting audio")

    _, stderr_output = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed (code {process.returncode}): {(stderr_output or '')[:500]}")

    logger.info("Trích xuất âm thanh hoàn tất: %s", output_path)
    return output_path


def burn_subtitles(
    input_video: str,
    subtitle_file: str,
    output_path: str,
    video_settings: dict | None = None,
    on_progress: ProgressCallback | None = None,
) -> str:
    """
    Ghi phụ đề vào video sử dụng bộ lọc libass.

    Args:
        input_video: Đường dẫn video đầu vào.
        subtitle_file: Đường dẫn tệp phụ đề (.srt, .ass, .vtt).
        output_path: Đường dẫn video đầu ra.
        video_settings: Cài đặt mã hóa tùy chọn (crf, preset).
        on_progress: Hàm callback tiến trình.
    """
    input_file = Path(input_video)
    sub_file = Path(subtitle_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Video not found: {input_video}")
    if not sub_file.exists():
        raise FileNotFoundError(f"Subtitle file not found: {subtitle_file}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    duration = get_duration(input_video)
    encoder = get_ffmpeg_encoder()
    vs = video_settings or {}

    # Escape subtitle path for ffmpeg filter (backslashes and colons)
    escaped_sub = str(sub_file).replace("\\", "/").replace(":", "\\:")

    # Build command based on subtitle format
    suffix = sub_file.suffix.lower()
    if suffix == ".ass":
        vf_filter = f"ass='{escaped_sub}'"
    else:
        vf_filter = f"subtitles='{escaped_sub}'"

    # Encoding quality from video_settings or defaults
    crf = vs.get("crf", 23)
    enc_preset = vs.get("preset", "medium")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i", input_video,
        "-vf", vf_filter,
        "-c:v", encoder,
        "-c:a", "copy",
    ]

    if encoder == "h264_nvenc":
        nvenc_preset = _map_preset_to_nvenc(enc_preset)
        cmd.extend(["-preset", nvenc_preset, "-cq", str(crf)])
    else:
        cmd.extend(["-preset", enc_preset, "-crf", str(crf)])

    use_progress = on_progress is not None and duration > 0
    if use_progress:
        cmd.extend(["-progress", "pipe:1"])

    cmd.append(output_path)

    logger.info("Đang ghi phụ đề: %s + %s -> %s (encoder: %s, crf=%s, preset=%s)",
                input_video, subtitle_file, output_path, encoder, crf, enc_preset)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE if use_progress else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if use_progress and process.stdout:
        _parse_ffmpeg_progress(process.stdout, duration, on_progress, "Burning subtitles")

    _, stderr_output = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg burn-in failed (code {process.returncode}): {(stderr_output or '')[:500]}")

    logger.info("Ghi phụ đề hoàn tất: %s", output_path)
    return output_path


def _map_preset_to_nvenc(preset: str) -> str:
    """Ánh xạ tên preset x264 sang tương đương NVENC."""
    mapping = {
        "ultrafast": "p1",
        "superfast": "p2",
        "veryfast": "p3",
        "faster": "p3",
        "fast": "p4",
        "medium": "p4",
        "slow": "p5",
        "slower": "p6",
        "veryslow": "p7",
    }
    return mapping.get(preset, "p4")


def get_duration(file_path: str) -> float:
    """Lấy thời lượng media tính bằng giây sử dụng ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to get duration for %s: %s", file_path, e)
    return 0.0


def get_video_info(file_path: str) -> dict:
    """Lấy thông tin chi tiết video sử dụng ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {"error": "ffprobe failed"}

        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])

        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

        info: dict = {
            "filename": fmt.get("filename", ""),
            "duration": float(fmt.get("duration", 0)),
            "size_bytes": int(fmt.get("size", 0)),
            "format_name": fmt.get("format_name", ""),
            "video": None,
            "audio_tracks": [],
            "subtitle_tracks": [],
        }

        if video_streams:
            vs = video_streams[0]
            info["video"] = {
                "codec": vs.get("codec_name", ""),
                "width": vs.get("width", 0),
                "height": vs.get("height", 0),
                "fps": _parse_fps(vs.get("r_frame_rate", "0/1")),
                "bitrate": int(vs.get("bit_rate", 0)),
            }

        for i, a_stream in enumerate(audio_streams):
            info["audio_tracks"].append({
                "index": i,
                "codec": a_stream.get("codec_name", ""),
                "language": a_stream.get("tags", {}).get("language", "und"),
                "channels": a_stream.get("channels", 0),
                "sample_rate": int(a_stream.get("sample_rate", 0)),
            })

        for i, s_stream in enumerate(subtitle_streams):
            info["subtitle_tracks"].append({
                "index": i,
                "codec": s_stream.get("codec_name", ""),
                "language": s_stream.get("tags", {}).get("language", "und"),
            })

        return info

    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to get video info for %s: %s", file_path, e)
        return {"error": str(e)}


def _parse_fps(rate_str: str) -> float:
    """Phân tích chuỗi tốc độ khung hình ffprobe như '30000/1001'."""
    try:
        if "/" in rate_str:
            num, den = rate_str.split("/")
            return round(float(num) / float(den), 2)
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _parse_ffmpeg_progress(
    stdout,
    total_duration: float,
    on_progress: ProgressCallback,
    step_name: str,
):
    """Phân tích đầu ra tiến trình ffmpeg và gọi callback."""
    time_pattern = re.compile(r"out_time_us=(\d+)")

    for line in stdout:
        match = time_pattern.search(line)
        if match:
            current_us = int(match.group(1))
            current_sec = current_us / 1_000_000
            percent = min((current_sec / total_duration) * 100, 100) if total_duration > 0 else 0
            on_progress(percent, f"{step_name}: {percent:.1f}%")
