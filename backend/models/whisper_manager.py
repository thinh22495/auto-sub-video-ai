from __future__ import annotations

import logging
import shutil
from pathlib import Path

from backend.config.settings import settings
from backend.video.hardware_detector import get_whisper_compute_type, get_whisper_device

logger = logging.getLogger(__name__)

# Các mô hình faster-whisper có sẵn cùng siêu dữ liệu
WHISPER_MODELS = {
    "tiny": {"size_mb": 75, "vram_mb": 1000, "speed": "nhanh nhất", "quality": "thấp"},
    "base": {"size_mb": 142, "vram_mb": 1000, "speed": "rất nhanh", "quality": "thấp-trung bình"},
    "small": {"size_mb": 466, "vram_mb": 2000, "speed": "nhanh", "quality": "trung bình"},
    "medium": {"size_mb": 1500, "vram_mb": 5000, "speed": "vừa phải", "quality": "tốt"},
    "large-v2": {"size_mb": 3100, "vram_mb": 10000, "speed": "chậm", "quality": "xuất sắc"},
    "large-v3": {"size_mb": 3100, "vram_mb": 10000, "speed": "chậm", "quality": "xuất sắc"},
    "large-v3-turbo": {"size_mb": 1600, "vram_mb": 6000, "speed": "vừa phải", "quality": "rất tốt"},
}


def list_models() -> list[dict]:
    """Liệt kê tất cả mô hình Whisper có sẵn cùng trạng thái tải xuống."""
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
    Tải mô hình Whisper bằng cách load qua faster-whisper.
    Mô hình được cache tự động bởi CTranslate2/huggingface_hub.
    """
    if model_name not in WHISPER_MODELS:
        raise ValueError(f"Mô hình không xác định: {model_name}. Có sẵn: {list(WHISPER_MODELS.keys())}")

    logger.info("Đang tải mô hình Whisper: %s", model_name)

    try:
        from faster_whisper import WhisperModel

        device = get_whisper_device()
        compute_type = get_whisper_compute_type()

        # Tải mô hình sẽ tự động tải xuống nếu chưa có trong cache
        _ = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )

        logger.info("Đã tải và load mô hình Whisper: %s", model_name)

        return {
            "name": model_name,
            "status": "downloaded",
            "device": device,
            "compute_type": compute_type,
        }

    except Exception as e:
        logger.error("Không thể tải mô hình Whisper %s: %s", model_name, e)
        raise RuntimeError(f"Không thể tải mô hình {model_name}: {e}")


def delete_model(model_name: str) -> bool:
    """Xóa mô hình Whisper đã cache khỏi ổ đĩa."""
    if model_name not in WHISPER_MODELS:
        raise ValueError(f"Mô hình không xác định: {model_name}")

    model_path = _get_model_cache_path(model_name)
    if model_path and model_path.exists():
        shutil.rmtree(model_path, ignore_errors=True)
        logger.info("Đã xóa mô hình Whisper: %s (%s)", model_name, model_path)

        # Xóa khỏi cache trong bộ nhớ nếu đã load
        from backend.core.transcriber import _model_cache
        keys_to_remove = [k for k in _model_cache if k.startswith(model_name)]
        for k in keys_to_remove:
            del _model_cache[k]

        return True

    logger.warning("Không tìm thấy mô hình trên ổ đĩa: %s", model_name)
    return False


def get_model_info(model_name: str) -> dict | None:
    """Lấy thông tin cho một mô hình cụ thể."""
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
    """Tìm thư mục mô hình đã cache. faster-whisper lưu trong HF cache."""
    # Cấu trúc cache HuggingFace hub
    hf_home = Path(settings.MODEL_DIR) / "huggingface"
    hub_dir = hf_home / "hub"

    if not hub_dir.exists():
        return None

    # Mô hình được cache dạng: models--Systran--faster-whisper-{name}
    expected_dir_name = f"models--Systran--faster-whisper-{model_name}"
    model_dir = hub_dir / expected_dir_name

    if model_dir.exists():
        return model_dir

    # Kiểm tra thêm cache CTranslate2 trực tiếp
    ct2_dir = Path(settings.MODEL_DIR) / "whisper" / model_name
    if ct2_dir.exists():
        return ct2_dir

    return None


def _dir_size_mb(path: Path) -> float:
    """Tính tổng dung lượng thư mục tính bằng MB."""
    if not path or not path.exists():
        return 0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)
