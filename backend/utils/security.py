"""Tiện ích ngăn chặn truy cập đường dẫn trái phép và làm sạch đầu vào."""

from __future__ import annotations

import os
from pathlib import Path

from backend.config.settings import settings

# Danh sách thư mục được phép truy cập và thao tác tệp
ALLOWED_ROOTS: list[str] = []


def _get_allowed_roots() -> list[str]:
    """Khởi tạo danh sách thư mục gốc được phép khi cần (lazy loading)."""
    if not ALLOWED_ROOTS:
        ALLOWED_ROOTS.extend([
            os.path.realpath(settings.VIDEO_INPUT_DIR),
            os.path.realpath(settings.SUBTITLE_OUTPUT_DIR),
            os.path.realpath(settings.VIDEO_OUTPUT_DIR),
        ])
    return ALLOWED_ROOTS


def is_safe_path(path: str, allowed_roots: list[str] | None = None) -> bool:
    """
    Kiểm tra xem đường dẫn có nằm trong các thư mục gốc được phép hay không.

    Ngăn chặn tấn công duyệt thư mục (ví dụ: ../../etc/passwd).
    """
    roots = allowed_roots or _get_allowed_roots()
    try:
        real = os.path.realpath(path)
        return any(real.startswith(root) for root in roots)
    except (OSError, ValueError):
        return False


def sanitize_path(path: str, allowed_roots: list[str] | None = None) -> Path:
    """
    Phân giải và xác thực đường dẫn. Ném ValueError nếu đường dẫn
    nằm ngoài các thư mục được phép.
    """
    resolved = Path(path).resolve()
    if not is_safe_path(str(resolved), allowed_roots):
        raise ValueError(f"Access denied: path is outside allowed directories")
    return resolved


def safe_join(base_dir: str, *parts: str) -> Path:
    """
    Nối các thành phần đường dẫn vào thư mục gốc một cách an toàn.
    Ném ValueError nếu kết quả vượt ra ngoài thư mục gốc.
    """
    base = Path(base_dir).resolve()
    target = (base / Path(*parts)).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Access denied: path traversal detected")
    return target


def sanitize_filename(filename: str) -> str:
    """
    Làm sạch tên tệp bằng cách loại bỏ các ký tự nguy hiểm.
    Giữ nguyên phần mở rộng nhưng loại bỏ dấu phân cách đường dẫn và ký tự đặc biệt.
    """
    # Loại bỏ các thành phần đường dẫn
    name = Path(filename).name

    # Thay thế các ký tự có vấn đề
    dangerous = set('<>:"|?*\x00')
    sanitized = "".join(c if c not in dangerous else "_" for c in name)

    # Ngăn tên tệp rỗng hoặc chỉ có dấu chấm
    if not sanitized or sanitized.startswith("."):
        sanitized = f"file_{sanitized}"

    return sanitized
