from __future__ import annotations

import logging
import shutil
from pathlib import Path

from backend.config.settings import settings
from backend.video.hardware_detector import get_whisper_compute_type, get_whisper_device

logger = logging.getLogger(__name__)

# Available faster-whisper models with metadata
WHISPER_MODELS = {
    "tiny": {"size_mb": 75, "vram_mb": 1000, "speed": "fastest", "quality": "low"},
    "base": {"size_mb": 142, "vram_mb": 1000, "speed": "very fast", "quality": "low-medium"},
    "small": {"size_mb": 466, "vram_mb": 2000, "speed": "fast", "quality": "medium"},
    "medium": {"size_mb": 1500, "vram_mb": 5000, "speed": "moderate", "quality": "good"},
    "large-v2": {"size_mb": 3100, "vram_mb": 10000, "speed": "slow", "quality": "excellent"},
    "large-v3": {"size_mb": 3100, "vram_mb": 10000, "speed": "slow", "quality": "excellent"},
    "large-v3-turbo": {"size_mb": 1600, "vram_mb": 6000, "speed": "moderate", "quality": "very good"},
}


def list_models() -> list[dict]:
    """List all available Whisper models with download status."""
    models_dir = Path(settings.MODEL_DIR) / "whisper"
    result = []

    for name, meta in WHISPER_MODELS.items():
        model_path = _get_model_cache_path(name)
        is_downloaded = model_path is not None and model_path.exists()
        size_on_disk = _dir_size_mb(model_path) if is_downloaded and model_path else 0

        result.append({
            "name": name,
            "downloaded": is_downloaded,
            "size_mb": meta["size_mb"],
            "size_on_disk_mb": round(size_on_disk, 1),
            "vram_mb": meta["vram_mb"],
            "speed": meta["speed"],
            "quality": meta["quality"],
            "is_default": model_name == settings.DEFAULT_WHISPER_MODEL,
        })

    return result


def download_model(model_name: str) -> dict:
    """
    Download a Whisper model by loading it with faster-whisper.
    The model is cached automatically by CTranslate2/huggingface_hub.
    """
    if model_name not in WHISPER_MODELS:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(WHISPER_MODELS.keys())}")

    logger.info("Downloading Whisper model: %s", model_name)

    try:
        from faster_whisper import WhisperModel

        device = get_whisper_device()
        compute_type = get_whisper_compute_type()

        # Loading the model triggers download if not cached
        _ = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )

        logger.info("Whisper model downloaded and loaded: %s", model_name)

        return {
            "name": model_name,
            "status": "downloaded",
            "device": device,
            "compute_type": compute_type,
        }

    except Exception as e:
        logger.error("Failed to download Whisper model %s: %s", model_name, e)
        raise RuntimeError(f"Failed to download model {model_name}: {e}")


def delete_model(model_name: str) -> bool:
    """Delete a cached Whisper model from disk."""
    if model_name not in WHISPER_MODELS:
        raise ValueError(f"Unknown model: {model_name}")

    model_path = _get_model_cache_path(model_name)
    if model_path and model_path.exists():
        shutil.rmtree(model_path, ignore_errors=True)
        logger.info("Deleted Whisper model: %s (%s)", model_name, model_path)

        # Also clear from in-memory cache if loaded
        from backend.core.transcriber import _model_cache
        keys_to_remove = [k for k in _model_cache if k.startswith(model_name)]
        for k in keys_to_remove:
            del _model_cache[k]

        return True

    logger.warning("Model not found on disk: %s", model_name)
    return False


def get_model_info(model_name: str) -> dict | None:
    """Get info for a specific model."""
    if model_name not in WHISPER_MODELS:
        return None

    meta = WHISPER_MODELS[model_name]
    model_path = _get_model_cache_path(model_name)
    is_downloaded = model_path is not None and model_path.exists()

    return {
        "name": model_name,
        "downloaded": is_downloaded,
        **meta,
        "is_default": model_name == settings.DEFAULT_WHISPER_MODEL,
    }


def _get_model_cache_path(model_name: str) -> Path | None:
    """Find the cached model directory. faster-whisper stores in HF cache."""
    # HuggingFace hub cache structure
    hf_home = Path(settings.MODEL_DIR) / "huggingface"
    hub_dir = hf_home / "hub"

    if not hub_dir.exists():
        return None

    # Models are cached as: models--Systran--faster-whisper-{name}
    expected_dir_name = f"models--Systran--faster-whisper-{model_name}"
    model_dir = hub_dir / expected_dir_name

    if model_dir.exists():
        return model_dir

    # Also check for direct CTranslate2 cache
    ct2_dir = Path(settings.MODEL_DIR) / "whisper" / model_name
    if ct2_dir.exists():
        return ct2_dir

    return None


def _dir_size_mb(path: Path) -> float:
    """Calculate total size of a directory in MB."""
    if not path or not path.exists():
        return 0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)
