from __future__ import annotations

import logging
import shutil
from pathlib import Path

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# Siêu dữ liệu mô hình pyannote
PYANNOTE_MODELS = {
    "pyannote/speaker-diarization-3.1": {
        "size_mb": 350,
        "description": "Pipeline phân biệt người nói v3.1",
        "requires_auth": True,
    },
    "pyannote/segmentation-3.0": {
        "size_mb": 60,
        "description": "Mô hình phân đoạn người nói v3.0",
        "requires_auth": True,
    },
}

# Cache trong bộ nhớ cho pipeline đã load
_pipeline_cache: dict[str, object] = {}


def get_model_dir() -> Path:
    return Path(settings.MODEL_DIR) / "pyannote"


def is_available() -> bool:
    """Kiểm tra xem pyannote.audio đã được cài đặt chưa."""
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
    Tải và cache pipeline phân biệt người nói pyannote.
    Lần gọi đầu tiên sẽ tải mô hình nếu chưa có trong cache.
    """
    cache_key = model_name
    if cache_key in _pipeline_cache:
        return _pipeline_cache[cache_key]

    if not is_available():
        raise RuntimeError(
            "pyannote.audio chưa được cài đặt. "
            "Cài đặt bằng: pip install pyannote.audio"
        )

    from pyannote.audio import Pipeline
    import torch

    logger.info("Đang tải pipeline pyannote: %s", model_name)

    cache_dir = get_model_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline.from_pretrained(
        model_name,
        use_auth_token=use_auth_token,
        cache_dir=str(cache_dir),
    )

    # Chuyển sang GPU nếu có
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline.to(device)

    logger.info("Đã tải pipeline pyannote trên %s", device)
    _pipeline_cache[cache_key] = pipeline
    return pipeline


def list_models() -> list[dict]:
    """Liệt kê các mô hình pyannote có sẵn cùng trạng thái."""
    cache_dir = get_model_dir()
    result = []

    for name, meta in PYANNOTE_MODELS.items():
        # Kiểm tra mô hình đã được cache cục bộ chưa
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
    """Xóa các tệp mô hình pyannote đã cache."""
    cache_dir = get_model_dir()
    if cache_dir.exists():
        # Xóa cache kiểu hub
        for d in cache_dir.iterdir():
            if d.is_dir() and model_name.replace("/", "--") in d.name:
                shutil.rmtree(d, ignore_errors=True)
                logger.info("Đã xóa cache mô hình pyannote: %s", d)

                # Xóa khỏi bộ nhớ
                _pipeline_cache.pop(model_name, None)
                return True

    return False


def _check_cached(model_name: str, cache_dir: Path) -> bool:
    """Kiểm tra xem mô hình đã được cache cục bộ chưa."""
    if not cache_dir.exists():
        return False

    safe_name = model_name.replace("/", "--")
    for d in cache_dir.iterdir():
        if d.is_dir() and safe_name in d.name:
            return True

    return False
