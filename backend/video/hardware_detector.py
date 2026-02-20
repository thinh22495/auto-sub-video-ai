from __future__ import annotations

import functools
import logging
import subprocess

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def detect_gpu() -> dict:
    """Detect NVIDIA GPU availability and capabilities. Result is cached."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            info = {
                "available": True,
                "name": parts[0] if len(parts) > 0 else "Unknown",
                "vram_total_mb": int(parts[1]) if len(parts) > 1 else 0,
                "vram_free_mb": int(parts[2]) if len(parts) > 2 else 0,
                "driver_version": parts[3] if len(parts) > 3 else "Unknown",
            }
            logger.info("GPU detected: %s (%dMB VRAM)", info["name"], info["vram_total_mb"])
            return info
    except FileNotFoundError:
        logger.info("nvidia-smi not found - running in CPU mode")
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi timed out")
    except Exception as e:
        logger.warning("GPU detection failed: %s", e)

    return {"available": False}


def get_whisper_device() -> str:
    """Return the best device for Whisper: 'cuda' or 'cpu'."""
    from backend.config.settings import settings

    if settings.WHISPER_DEVICE != "auto":
        return settings.WHISPER_DEVICE

    gpu = detect_gpu()
    return "cuda" if gpu["available"] else "cpu"


def get_whisper_compute_type() -> str:
    """Return the best compute type based on hardware."""
    from backend.config.settings import settings

    if settings.WHISPER_COMPUTE_TYPE != "auto":
        return settings.WHISPER_COMPUTE_TYPE

    device = get_whisper_device()
    return "float16" if device == "cuda" else "int8"


def get_ffmpeg_encoder() -> str:
    """Return the best video encoder: 'h264_nvenc' or 'libx264'."""
    gpu = detect_gpu()
    if not gpu["available"]:
        return "libx264"

    # Check if nvenc is available in ffmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "h264_nvenc" in result.stdout:
            return "h264_nvenc"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "libx264"


def get_ffmpeg_decoder() -> str:
    """Return the best H.264 decoder: 'h264_cuvid' or default."""
    gpu = detect_gpu()
    if not gpu["available"]:
        return "h264"

    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-decoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if "h264_cuvid" in result.stdout:
            return "h264_cuvid"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "h264"
