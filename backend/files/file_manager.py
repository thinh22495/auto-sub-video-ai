"""Các thao tác duyệt tệp, tải lên và tải xuống."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from backend.config.settings import settings
from backend.files.video_info import VIDEO_EXTENSIONS, is_video_file
from backend.utils.security import is_safe_path, safe_join, sanitize_filename

logger = logging.getLogger(__name__)

# File categories
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".vtt", ".sub", ".ssa"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}


def browse_directory(path: str | None = None) -> dict:
    """
    Liệt kê nội dung thư mục.

    Trả về tệp và thư mục con kèm metadata.
    Chỉ cho phép trong các thư mục dữ liệu đã cấu hình.
    """
    if path is None:
        path = settings.VIDEO_INPUT_DIR

    real_path = Path(path).resolve()

    # Validate the path is within allowed roots
    allowed = [
        os.path.realpath(settings.VIDEO_INPUT_DIR),
        os.path.realpath(settings.SUBTITLE_OUTPUT_DIR),
        os.path.realpath(settings.VIDEO_OUTPUT_DIR),
    ]
    if not is_safe_path(str(real_path), allowed):
        raise PermissionError(f"Truy cập bị từ chối: đường dẫn ngoài thư mục cho phép")

    if not real_path.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục: {path}")
    if not real_path.is_dir():
        raise ValueError(f"Không phải thư mục: {path}")

    items = []
    try:
        for entry in sorted(real_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                stat = entry.stat()
                item = {
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size_bytes": stat.st_size if entry.is_file() else 0,
                    "modified": stat.st_mtime,
                }

                if entry.is_file():
                    suffix = entry.suffix.lower()
                    if suffix in VIDEO_EXTENSIONS:
                        item["type"] = "video"
                    elif suffix in SUBTITLE_EXTENSIONS:
                        item["type"] = "subtitle"
                    elif suffix in AUDIO_EXTENSIONS:
                        item["type"] = "audio"
                    else:
                        item["type"] = "other"
                else:
                    item["type"] = "directory"

                items.append(item)
            except (PermissionError, OSError):
                continue
    except PermissionError:
        raise PermissionError(f"Không thể đọc thư mục: {path}")

    return {
        "path": str(real_path),
        "parent": str(real_path.parent) if str(real_path) != str(real_path.parent) else None,
        "items": items,
    }


def get_root_directories() -> list[dict]:
    """Trả về danh sách các thư mục gốc có thể duyệt."""
    roots = [
        {"name": "Videos", "path": settings.VIDEO_INPUT_DIR, "description": "Video đầu vào"},
        {"name": "Subtitles", "path": settings.SUBTITLE_OUTPUT_DIR, "description": "Phụ đề đã tạo"},
        {"name": "Output", "path": settings.VIDEO_OUTPUT_DIR, "description": "Video đầu ra có phụ đề"},
    ]

    result = []
    for root in roots:
        p = Path(root["path"])
        p.mkdir(parents=True, exist_ok=True)
        try:
            file_count = sum(1 for f in p.iterdir() if f.is_file())
        except OSError:
            file_count = 0

        result.append({
            **root,
            "exists": p.exists(),
            "file_count": file_count,
        })

    return result


def save_upload(
    filename: str,
    content: bytes,
    target_dir: str | None = None,
) -> str:
    """
    Lưu tệp đã tải lên vào thư mục đích.

    Trả về đường dẫn đầy đủ đến tệp đã lưu.
    """
    if target_dir is None:
        target_dir = settings.VIDEO_INPUT_DIR

    # Validate target is within allowed directories
    allowed = [os.path.realpath(settings.VIDEO_INPUT_DIR)]
    if not is_safe_path(os.path.realpath(target_dir), allowed):
        raise PermissionError("Thư mục tải lên không được phép")

    safe_name = sanitize_filename(filename)
    target_path = safe_join(target_dir, safe_name)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # If file already exists, add a number suffix
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = target_path.parent / f"{stem}_{counter}{suffix}"
            counter += 1

    target_path.write_bytes(content)
    logger.info("Đã tải lên tệp: %s (%d bytes)", target_path, len(content))
    return str(target_path)


def save_upload_chunk(
    filename: str,
    chunk: bytes,
    chunk_index: int,
    total_chunks: int,
    upload_id: str,
) -> dict:
    """
    Lưu một phần của tệp tải lên. Dùng cho tải lên tệp lớn.

    Trả về thông tin trạng thái bao gồm trạng thái hoàn thành.
    """
    temp_dir = Path(settings.TEMP_DIR) / "uploads" / upload_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    chunk_path = temp_dir / f"chunk_{chunk_index:06d}"
    chunk_path.write_bytes(chunk)

    # Check if all chunks are received
    received = len(list(temp_dir.glob("chunk_*")))

    if received >= total_chunks:
        # Assemble file
        safe_name = sanitize_filename(filename)
        target = Path(settings.VIDEO_INPUT_DIR) / safe_name

        # Handle duplicate filenames
        if target.exists():
            stem = target.stem
            suffix = target.suffix
            counter = 1
            while target.exists():
                target = target.parent / f"{stem}_{counter}{suffix}"
                counter += 1

        with open(target, "wb") as out:
            for i in range(total_chunks):
                cp = temp_dir / f"chunk_{i:06d}"
                if cp.exists():
                    out.write(cp.read_bytes())

        # Cleanup temp chunks
        shutil.rmtree(temp_dir, ignore_errors=True)

        logger.info("Tải lên phân đoạn hoàn tất: %s (%d phần)", target, total_chunks)
        return {
            "status": "completed",
            "path": str(target),
            "filename": target.name,
        }

    return {
        "status": "uploading",
        "received": received,
        "total": total_chunks,
    }


def delete_file(path: str) -> bool:
    """Xóa tệp nếu nằm trong thư mục cho phép."""
    allowed = [
        os.path.realpath(settings.VIDEO_INPUT_DIR),
        os.path.realpath(settings.SUBTITLE_OUTPUT_DIR),
        os.path.realpath(settings.VIDEO_OUTPUT_DIR),
    ]
    if not is_safe_path(path, allowed):
        raise PermissionError("Không thể xóa tệp ngoài thư mục cho phép")

    p = Path(path)
    if not p.exists():
        return False
    if p.is_dir():
        raise ValueError("Không thể xóa thư mục qua endpoint này")

    p.unlink()
    logger.info("Đã xóa tệp: %s", path)
    return True


def get_disk_usage(path: str) -> dict:
    """Lấy thông tin sử dụng đĩa cho đường dẫn."""
    try:
        usage = shutil.disk_usage(path)
        return {
            "total_gb": round(usage.total / (1024 ** 3), 1),
            "free_gb": round(usage.free / (1024 ** 3), 1),
            "used_gb": round(usage.used / (1024 ** 3), 1),
            "used_percent": round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0,
        }
    except OSError:
        return {"total_gb": 0, "free_gb": 0, "used_gb": 0, "used_percent": 0}
