from __future__ import annotations

import functools
import logging
import subprocess

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def detect_gpu() -> dict:
    """Phát hiện GPU NVIDIA khả dụng và khả năng. Kết quả được lưu cache."""
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
            logger.info("Phát hiện GPU: %s (%dMB VRAM)", info["name"], info["vram_total_mb"])
            return info
    except FileNotFoundError:
        logger.info("Không tìm thấy nvidia-smi - chạy chế độ CPU")
    except subprocess.TimeoutExpired:
        logger.warning("nvidia-smi hết thời gian chờ")
    except Exception as e:
        logger.warning("Phát hiện GPU thất bại: %s", e)

    return {"available": False}


def get_whisper_device() -> str:
    """Trả về thiết bị tốt nhất cho Whisper: 'cuda' hoặc 'cpu'."""
    from backend.config.settings import settings

    if settings.WHISPER_DEVICE != "auto":
        return settings.WHISPER_DEVICE

    gpu = detect_gpu()
    return "cuda" if gpu["available"] else "cpu"


def get_whisper_compute_type() -> str:
    """Trả về loại tính toán tốt nhất dựa trên phần cứng."""
    from backend.config.settings import settings

    if settings.WHISPER_COMPUTE_TYPE != "auto":
        return settings.WHISPER_COMPUTE_TYPE

    device = get_whisper_device()
    return "float16" if device == "cuda" else "int8"


def get_ffmpeg_encoder() -> str:
    """Trả về bộ mã hóa video tốt nhất: 'h264_nvenc' hoặc 'libx264'."""
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


def get_ffmpeg_encoder_for_codec(codec: str | None = None) -> str:
    """Trả về bộ mã hóa tốt nhất cho codec được chỉ định."""
    if codec is None or codec == "h264":
        return get_ffmpeg_encoder()

    gpu = detect_gpu()

    if codec in ("h265", "hevc"):
        if gpu["available"]:
            try:
                result = subprocess.run(
                    ["ffmpeg", "-hide_banner", "-encoders"],
                    capture_output=True, text=True, timeout=5,
                )
                if "hevc_nvenc" in result.stdout:
                    return "hevc_nvenc"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return "libx265"

    if codec == "vp9":
        return "libvpx-vp9"

    # Fallback
    return get_ffmpeg_encoder()


def get_ffmpeg_decoder() -> str:
    """Trả về bộ giải mã H.264 tốt nhất: 'h264_cuvid' hoặc mặc định."""
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
