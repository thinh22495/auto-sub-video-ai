from __future__ import annotations

import logging
import shutil
from pathlib import Path

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# pyannote models metadata
PYANNOTE_MODELS = {
    "pyannote/speaker-diarization-3.1": {
        "size_mb": 350,
        "description": "Speaker diarization pipeline v3.1",
        "requires_auth": True,
    },
    "pyannote/segmentation-3.0": {
        "size_mb": 60,
        "description": "Speaker segmentation model v3.0",
        "requires_auth": True,
    },
}

# In-memory cache for loaded pipeline
_pipeline_cache: dict[str, object] = {}


def get_model_dir() -> Path:
    return Path(settings.MODEL_DIR) / "pyannote"


def is_available() -> bool:
    """Check if pyannote.audio is installed."""
    try:
        import pyannote.audio  # noqa: F401
        return True
    except ImportError:
        return False


def get_pipeline(
    model_name: str = "pyannote/speaker-diarization-3.1",
    use_auth_token: str | None = None,
):
    """
    Load and cache the pyannote diarization pipeline.
    On first call, downloads the model if not cached.
    """
    cache_key = model_name
    if cache_key in _pipeline_cache:
        return _pipeline_cache[cache_key]

    if not is_available():
        raise RuntimeError(
            "pyannote.audio is not installed. "
            "Install with: pip install pyannote.audio"
        )

    from pyannote.audio import Pipeline
    import torch

    logger.info("Loading pyannote pipeline: %s", model_name)

    cache_dir = get_model_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline.from_pretrained(
        model_name,
        use_auth_token=use_auth_token,
        cache_dir=str(cache_dir),
    )

    # Move to GPU if available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline.to(device)

    logger.info("pyannote pipeline loaded on %s", device)
    _pipeline_cache[cache_key] = pipeline
    return pipeline


def list_models() -> list[dict]:
    """List available pyannote models with status."""
    cache_dir = get_model_dir()
    result = []

    for name, meta in PYANNOTE_MODELS.items():
        # Check if model is cached locally
        is_downloaded = _check_cached(name, cache_dir)
        result.append({
            "name": name,
            "downloaded": is_downloaded,
            "size_mb": meta["size_mb"],
            "description": meta["description"],
            "requires_auth": meta["requires_auth"],
        })

    return result


def delete_model(model_name: str) -> bool:
    """Delete cached pyannote model files."""
    cache_dir = get_model_dir()
    if cache_dir.exists():
        # Remove hub-style cache
        for d in cache_dir.iterdir():
            if d.is_dir() and model_name.replace("/", "--") in d.name:
                shutil.rmtree(d, ignore_errors=True)
                logger.info("Deleted pyannote model cache: %s", d)

                # Clear from memory
                _pipeline_cache.pop(model_name, None)
                return True

    return False


def _check_cached(model_name: str, cache_dir: Path) -> bool:
    """Check if a model is already cached locally."""
    if not cache_dir.exists():
        return False

    safe_name = model_name.replace("/", "--")
    for d in cache_dir.iterdir():
        if d.is_dir() and safe_name in d.name:
            return True

    return False
