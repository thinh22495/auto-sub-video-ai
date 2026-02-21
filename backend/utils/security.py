"""Path traversal prevention and input sanitization utilities."""

from __future__ import annotations

import os
from pathlib import Path

from backend.config.settings import settings

# Directories that are allowed for file browsing and operations
ALLOWED_ROOTS: list[str] = []


def _get_allowed_roots() -> list[str]:
    """Lazily build the set of allowed root directories."""
    if not ALLOWED_ROOTS:
        ALLOWED_ROOTS.extend([
            os.path.realpath(settings.VIDEO_INPUT_DIR),
            os.path.realpath(settings.SUBTITLE_OUTPUT_DIR),
            os.path.realpath(settings.VIDEO_OUTPUT_DIR),
        ])
    return ALLOWED_ROOTS


def is_safe_path(path: str, allowed_roots: list[str] | None = None) -> bool:
    """
    Check if a path is within one of the allowed root directories.

    Prevents directory traversal attacks (e.g. ../../etc/passwd).
    """
    roots = allowed_roots or _get_allowed_roots()
    try:
        real = os.path.realpath(path)
        return any(real.startswith(root) for root in roots)
    except (OSError, ValueError):
        return False


def sanitize_path(path: str, allowed_roots: list[str] | None = None) -> Path:
    """
    Resolve and validate a path. Raises ValueError if the path
    escapes the allowed directories.
    """
    resolved = Path(path).resolve()
    if not is_safe_path(str(resolved), allowed_roots):
        raise ValueError(f"Access denied: path is outside allowed directories")
    return resolved


def safe_join(base_dir: str, *parts: str) -> Path:
    """
    Safely join path components to a base directory.
    Raises ValueError if the result escapes the base.
    """
    base = Path(base_dir).resolve()
    target = (base / Path(*parts)).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Access denied: path traversal detected")
    return target


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing dangerous characters.
    Preserves extension but strips path separators and special chars.
    """
    # Remove any path components
    name = Path(filename).name

    # Replace problematic characters
    dangerous = set('<>:"|?*\x00')
    sanitized = "".join(c if c not in dangerous else "_" for c in name)

    # Prevent empty or dot-only names
    if not sanitized or sanitized.startswith("."):
        sanitized = f"file_{sanitized}"

    return sanitized
