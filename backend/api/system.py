import platform
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter

from backend.config.settings import settings

router = APIRouter(tags=["system"])


def _check_gpu() -> dict:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            return {
                "available": True,
                "name": parts[0] if len(parts) > 0 else "Unknown",
                "vram_total_mb": int(parts[1]) if len(parts) > 1 else 0,
                "vram_free_mb": int(parts[2]) if len(parts) > 2 else 0,
            }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return {"available": False}


def _check_redis() -> bool:
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_timeout=2)
        return r.ping()
    except Exception:
        return False


def _check_ollama() -> bool:
    try:
        import httpx
        resp = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def _disk_usage(path: str) -> dict:
    try:
        usage = shutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "used_percent": round((usage.used / usage.total) * 100, 1),
        }
    except OSError:
        return {"total_gb": 0, "free_gb": 0, "used_percent": 0}


@router.get("/health")
async def health_check():
    redis_ok = _check_redis()
    ollama_ok = _check_ollama()
    gpu_info = _check_gpu()

    all_healthy = redis_ok  # Ollama is optional for health check

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "api": "up",
            "redis": "up" if redis_ok else "down",
            "ollama": "up" if ollama_ok else "down",
            "gpu": gpu_info,
        },
        "disk": {
            "videos": _disk_usage(settings.VIDEO_INPUT_DIR),
            "models": _disk_usage(settings.MODEL_DIR),
        },
    }


@router.get("/system/info")
async def system_info():
    gpu_info = _check_gpu()

    ffmpeg_version = "not found"
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            ffmpeg_version = result.stdout.split("\n")[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "ffmpeg_version": ffmpeg_version,
        "gpu": gpu_info,
        "settings": {
            "whisper_model": settings.DEFAULT_WHISPER_MODEL,
            "ollama_model": settings.DEFAULT_OLLAMA_MODEL,
            "whisper_device": settings.WHISPER_DEVICE,
            "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
        },
    }
