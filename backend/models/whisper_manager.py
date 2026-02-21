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


def _check_model_cached(model_name: str) -> tuple[bool, Path | None, float]:
    """
    Kiểm tra mô hình đã được cache chưa.
    Trả về (is_cached, snapshot_path, size_on_disk_mb).
    """
    repo_id = f"Systran/faster-whisper-{model_name}"

    # Phương pháp 1: dùng snapshot_download(local_files_only=True)
    # Đây là cách chính xác nhất - dùng đúng logic của faster-whisper/huggingface_hub
    try:
        from huggingface_hub import snapshot_download
        path = snapshot_download(repo_id, local_files_only=True)
        snapshot_path = Path(path)
        size_mb = _dir_size_mb(snapshot_path)
        logger.debug("Tìm thấy mô hình %s qua snapshot_download: %s", model_name, path)
        return True, snapshot_path, size_mb
    except Exception as e:
        logger.debug("snapshot_download cho %s thất bại: %s", model_name, e)

    # Phương pháp 2: tìm thủ công thư mục HF cache
    expected_dir = f"models--Systran--faster-whisper-{model_name}"
    for hub_dir in _get_hf_cache_dirs():
        model_dir = hub_dir / expected_dir
        if model_dir.exists():
            # Kiểm tra có snapshot thực sự (không chỉ thư mục rỗng)
            snapshots_dir = model_dir / "snapshots"
            if snapshots_dir.exists() and any(snapshots_dir.iterdir()):
                size_mb = _dir_size_mb(model_dir)
                logger.debug("Tìm thấy mô hình %s thủ công: %s", model_name, model_dir)
                return True, model_dir, size_mb

    # Phương pháp 3: cache CTranslate2 trực tiếp
    ct2_dir = Path(settings.MODEL_DIR) / "whisper" / model_name
    if ct2_dir.exists() and any(ct2_dir.iterdir()):
        size_mb = _dir_size_mb(ct2_dir)
        logger.debug("Tìm thấy mô hình %s tại CT2 cache: %s", model_name, ct2_dir)
        return True, ct2_dir, size_mb

    logger.debug("Không tìm thấy mô hình %s trong cache", model_name)
    return False, None, 0


def _get_hf_cache_dirs() -> list[Path]:
    """Lấy danh sách các thư mục HuggingFace hub cache có thể."""
    import os

    dirs: list[Path] = []
    seen: set[str] = set()

    def _add(p: Path) -> None:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key not in seen and p.exists():
            seen.add(key)
            dirs.append(p)

    # Từ huggingface_hub constants (ưu tiên cao nhất)
    try:
        from huggingface_hub import constants as hf_constants
        _add(Path(hf_constants.HF_HUB_CACHE))
    except Exception:
        pass

    # Từ biến môi trường HF_HOME
    hf_home = os.environ.get("HF_HOME")
    if hf_home:
        _add(Path(hf_home) / "hub")

    # Từ MODEL_DIR setting
    _add(Path(settings.MODEL_DIR) / "huggingface" / "hub")

    # Đường dẫn mặc định
    _add(Path.home() / ".cache" / "huggingface" / "hub")

    return dirs


def list_models() -> list[dict]:
    """Liệt kê tất cả mô hình Whisper có sẵn cùng trạng thái tải xuống."""
    result = []

    for name, meta in WHISPER_MODELS.items():
        is_downloaded, _, size_on_disk = _check_model_cached(name)

        result.append({
            "name": name,
            "downloaded": is_downloaded,
            "size_mb": meta["size_mb"],
            "size_on_disk_mb": round(size_on_disk, 1),
            "vram_mb": meta["vram_mb"],
            "speed": meta["speed"],
            "quality": meta["quality"],
            "is_default": name == settings.DEFAULT_WHISPER_MODEL,
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

    is_cached, model_path, _ = _check_model_cached(model_name)
    if is_cached and model_path and model_path.exists():
        # Nếu path là snapshot, xóa toàn bộ repo dir (models--Systran--...)
        repo_dir = model_path
        for parent in [model_path] + list(model_path.parents):
            if parent.name.startswith("models--Systran--faster-whisper-"):
                repo_dir = parent
                break

        shutil.rmtree(repo_dir, ignore_errors=True)
        logger.info("Đã xóa mô hình Whisper: %s (%s)", model_name, repo_dir)

        # Xóa khỏi cache trong bộ nhớ nếu đã load
        try:
            from backend.core.transcriber import _model_cache
            keys_to_remove = [k for k in _model_cache if k.startswith(model_name)]
            for k in keys_to_remove:
                del _model_cache[k]
        except ImportError:
            pass

        return True

    logger.warning("Không tìm thấy mô hình trên ổ đĩa: %s", model_name)
    return False


def get_model_info(model_name: str) -> dict | None:
    """Lấy thông tin cho một mô hình cụ thể."""
    if model_name not in WHISPER_MODELS:
        return None

    meta = WHISPER_MODELS[model_name]
    is_downloaded, _, size_on_disk = _check_model_cached(model_name)

    return {
        "name": model_name,
        "downloaded": is_downloaded,
        "size_on_disk_mb": round(size_on_disk, 1),
        **meta,
        "is_default": model_name == settings.DEFAULT_WHISPER_MODEL,
    }


def _dir_size_mb(path: Path) -> float:
    """Tính tổng dung lượng thư mục tính bằng MB."""
    if not path or not path.exists():
        return 0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)
