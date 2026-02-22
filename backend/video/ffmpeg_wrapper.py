from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from backend.config.settings import settings
from backend.video.hardware_detector import get_ffmpeg_decoder, get_ffmpeg_encoder, get_ffmpeg_encoder_for_codec

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


def _build_video_encode_cmd(
    input_video: str,
    output_path: str,
    video_settings: dict | None = None,
    vf_filters: list[str] | None = None,
) -> list[str]:
    """Tạo lệnh ffmpeg với cài đặt video mã hóa."""
    vs = video_settings or {}

    # Chọn encoder theo codec yêu cầu
    requested_codec = vs.get("video_codec")
    encoder = get_ffmpeg_encoder_for_codec(requested_codec)

    # Xây dựng chuỗi video filter
    filters = list(vf_filters or [])

    # Thay đổi độ phân giải
    resolution = vs.get("resolution")
    if resolution:
        scale_map = {"1080p": "1920:-2", "720p": "1280:-2", "480p": "854:-2"}
        if resolution in scale_map:
            filters.append(f"scale={scale_map[resolution]}")

    # Thay đổi FPS
    fps = vs.get("fps")
    if fps:
        filters.append(f"fps={fps}")

    # Chất lượng mã hóa
    crf = vs.get("crf", 23)
    enc_preset = vs.get("preset", "medium")

    # Audio
    audio_codec = vs.get("audio_codec", "copy")
    audio_bitrate = vs.get("audio_bitrate", 128)

    # WebM: bắt buộc opus nếu audio=copy (AAC không tương thích webm)
    output_ext = Path(output_path).suffix.lower()
    if output_ext == ".webm" and audio_codec == "copy":
        audio_codec = "opus"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i", input_video,
    ]

    if filters:
        cmd.extend(["-vf", ",".join(filters)])

    cmd.extend(["-c:v", encoder])

    # Tham số chất lượng theo encoder
    if encoder in ("h264_nvenc", "hevc_nvenc"):
        nvenc_preset = _map_preset_to_nvenc(enc_preset)
        cmd.extend(["-preset", nvenc_preset, "-cq", str(crf)])
    elif encoder == "libvpx-vp9":
        cmd.extend(["-crf", str(crf), "-b:v", "0"])
    else:  # libx264, libx265
        cmd.extend(["-preset", enc_preset, "-crf", str(crf)])

    # Audio encoding
    if audio_codec == "copy":
        cmd.extend(["-c:a", "copy"])
    elif audio_codec == "aac":
        cmd.extend(["-c:a", "aac", "-b:a", f"{audio_bitrate}k"])
    elif audio_codec == "opus":
        cmd.extend(["-c:a", "libopus", "-b:a", f"{audio_bitrate}k"])

    return cmd


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
        video_settings: Cài đặt mã hóa tùy chọn (crf, preset, video_codec, resolution, ...).
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

    # Tạo subtitle filter
    escaped_sub = str(sub_file).replace("\\", "/").replace(":", "\\:")
    suffix = sub_file.suffix.lower()
    if suffix == ".ass":
        sub_filter = f"ass='{escaped_sub}'"
    else:
        sub_filter = f"subtitles='{escaped_sub}'"

    cmd = _build_video_encode_cmd(input_video, output_path, video_settings, vf_filters=[sub_filter])

    use_progress = on_progress is not None and duration > 0
    if use_progress:
        cmd.extend(["-progress", "pipe:1"])
    cmd.append(output_path)

    vs = video_settings or {}
    logger.info("Đang ghi phụ đề: %s + %s -> %s (codec=%s, crf=%s, preset=%s)",
                input_video, subtitle_file, output_path,
                vs.get("video_codec", "auto"), vs.get("crf", 23), vs.get("preset", "medium"))

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


def convert_video(
    input_video: str,
    output_path: str,
    video_settings: dict | None = None,
    on_progress: ProgressCallback | None = None,
) -> str:
    """
    Chuyển đổi video sang định dạng/codec/chất lượng khác (không gắn phụ đề).

    Args:
        input_video: Đường dẫn video đầu vào.
        output_path: Đường dẫn video đầu ra.
        video_settings: Cài đặt mã hóa (output_format, video_codec, crf, preset, resolution, ...).
        on_progress: Hàm callback tiến trình.
    """
    input_file = Path(input_video)
    if not input_file.exists():
        raise FileNotFoundError(f"Video not found: {input_video}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    duration = get_duration(input_video)

    cmd = _build_video_encode_cmd(input_video, output_path, video_settings)

    use_progress = on_progress is not None and duration > 0
    if use_progress:
        cmd.extend(["-progress", "pipe:1"])
    cmd.append(output_path)

    vs = video_settings or {}
    logger.info("Đang chuyển đổi video: %s -> %s (codec=%s, crf=%s, preset=%s)",
                input_video, output_path,
                vs.get("video_codec", "auto"), vs.get("crf", 23), vs.get("preset", "medium"))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE if use_progress else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if use_progress and process.stdout:
        _parse_ffmpeg_progress(process.stdout, duration, on_progress, "Converting video")

    _, stderr_output = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg convert failed (code {process.returncode}): {(stderr_output or '')[:500]}")

    logger.info("Chuyển đổi video hoàn tất: %s", output_path)
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
