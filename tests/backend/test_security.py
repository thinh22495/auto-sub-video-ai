"""Tests for security utilities."""

import os
import tempfile
from pathlib import Path

import pytest

from backend.utils.security import (
    is_safe_path,
    safe_join,
    sanitize_filename,
    sanitize_path,
)


@pytest.fixture
def allowed_dir(tmp_path):
    """Create a temporary allowed directory."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    (allowed / "test.txt").write_text("test")
    return str(allowed)


class TestIsSafePath:
    def test_safe_path(self, allowed_dir):
        path = os.path.join(allowed_dir, "test.txt")
        assert is_safe_path(path, [allowed_dir]) is True

    def test_traversal_blocked(self, allowed_dir):
        path = os.path.join(allowed_dir, "..", "..", "etc", "passwd")
        assert is_safe_path(path, [allowed_dir]) is False

    def test_absolute_escape(self, allowed_dir):
        assert is_safe_path("/etc/passwd", [allowed_dir]) is False

    def test_nested_subdirectory(self, allowed_dir):
        subdir = os.path.join(allowed_dir, "sub", "dir")
        os.makedirs(subdir, exist_ok=True)
        assert is_safe_path(os.path.join(subdir, "file.txt"), [allowed_dir]) is True


class TestSafetizeFilename:
    def test_normal_filename(self):
        assert sanitize_filename("video.mp4") == "video.mp4"

    def test_path_separators_stripped(self):
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert "\\" not in result

    def test_dangerous_chars_replaced(self):
        result = sanitize_filename('test<>:"|?.mp4')
        assert "<" not in result
        assert ">" not in result
        assert "?" not in result

    def test_empty_filename(self):
        result = sanitize_filename("")
        assert len(result) > 0

    def test_dot_prefix(self):
        result = sanitize_filename(".hidden")
        assert result.startswith("file_")


class TestSafeJoin:
    def test_normal_join(self, allowed_dir):
        result = safe_join(allowed_dir, "test.txt")
        assert str(result).startswith(os.path.realpath(allowed_dir))

    def test_traversal_raises(self, allowed_dir):
        with pytest.raises(ValueError, match="path traversal"):
            safe_join(allowed_dir, "..", "..", "etc", "passwd")

    def test_nested_join(self, allowed_dir):
        result = safe_join(allowed_dir, "sub", "dir", "file.txt")
        assert str(result).startswith(os.path.realpath(allowed_dir))


class TestSanitizePath:
    def test_valid_path(self, allowed_dir):
        path = os.path.join(allowed_dir, "test.txt")
        result = sanitize_path(path, [allowed_dir])
        assert result.exists()

    def test_traversal_raises(self, allowed_dir):
        path = os.path.join(allowed_dir, "..", "..", "etc", "passwd")
        with pytest.raises(ValueError, match="Access denied"):
            sanitize_path(path, [allowed_dir])
