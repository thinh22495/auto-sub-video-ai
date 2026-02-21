"""Phân loại lỗi và các kiểu ngoại lệ cho AutoSubAI.

Lỗi được phân loại thành:
- Tạm thời (Transient): lỗi tạm thời có thể thành công khi thử lại (mạng, tranh chấp tài nguyên)
- Vĩnh viễn (Permanent): lỗi không thể khắc phục nếu không có sự can thiệp của người dùng (đầu vào sai, thiếu mô hình)
"""

from enum import Enum


class ErrorCategory(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class AutoSubError(Exception):
    """Ngoại lệ cơ sở cho AutoSubAI."""

    category: ErrorCategory = ErrorCategory.PERMANENT
    user_message: str = "An unexpected error occurred."

    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        if user_message:
            self.user_message = user_message


# --- Lỗi tạm thời (có thể tự động thử lại) ---


class TransientError(AutoSubError):
    """Lớp cơ sở cho các lỗi có thể thành công khi thử lại."""

    category = ErrorCategory.TRANSIENT


class OllamaConnectionError(TransientError):
    """Không thể kết nối đến máy chủ Ollama."""

    user_message = "Translation service temporarily unavailable. Will retry."


class RedisConnectionError(TransientError):
    """Kết nối Redis thất bại."""

    user_message = "Task queue temporarily unavailable."


class GPUMemoryError(TransientError):
    """GPU hết bộ nhớ — có thể giải phóng sau khi các tác vụ khác hoàn thành."""

    user_message = "GPU memory full. Job will retry when resources are available."


class ResourceBusyError(TransientError):
    """Tài nguyên đang bị khóa bởi tiến trình khác."""

    user_message = "System resources are busy. Will retry shortly."


# --- Lỗi vĩnh viễn (cần người dùng xử lý) ---


class PermanentError(AutoSubError):
    """Lớp cơ sở cho các lỗi không thể khắc phục nếu không có sự can thiệp của người dùng."""

    category = ErrorCategory.PERMANENT


class FileNotFoundError(PermanentError):
    """Tệp đầu vào không tồn tại."""

    user_message = "The specified file was not found."


class InvalidFileError(PermanentError):
    """Định dạng tệp không được hỗ trợ hoặc bị hỏng."""

    user_message = "The file is not a supported video format or is corrupted."


class ModelNotFoundError(PermanentError):
    """Mô hình AI cần thiết chưa được tải xuống."""

    user_message = "Required model is not available. Please download it first."


class TranscriptionError(PermanentError):
    """Whisper không thể xử lý âm thanh."""

    user_message = "Failed to transcribe audio. The file may be corrupted or contain no speech."


class TranslationError(PermanentError):
    """Ollama tạo ra kết quả dịch không hợp lệ."""

    user_message = "Translation failed. Try a different model or language pair."


class FFmpegError(PermanentError):
    """Xử lý FFmpeg thất bại."""

    user_message = "Video processing failed. The file may be corrupted or use an unsupported codec."


class SecurityError(PermanentError):
    """Vi phạm bảo mật: duyệt đường dẫn trái phép hoặc vi phạm khác."""

    user_message = "Access denied: invalid file path."


# --- Các hàm hỗ trợ phân loại lỗi ---

# Các chuỗi con trong thông báo lỗi cho biết đây là lỗi tạm thời
_TRANSIENT_PATTERNS = [
    "connection refused",
    "connection reset",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "cuda out of memory",
    "out of memory",
    "resource busy",
    "too many open files",
    "no space left on device",
    "broken pipe",
    "connection aborted",
]


def classify_error(error: Exception) -> ErrorCategory:
    """Phân loại một ngoại lệ bất kỳ thành tạm thời hoặc vĩnh viễn."""
    if isinstance(error, AutoSubError):
        return error.category

    msg = str(error).lower()
    for pattern in _TRANSIENT_PATTERNS:
        if pattern in msg:
            return ErrorCategory.TRANSIENT

    return ErrorCategory.PERMANENT


def is_retryable(error: Exception) -> bool:
    """Check if an error should trigger an automatic retry."""
    return classify_error(error) == ErrorCategory.TRANSIENT


def get_user_message(error: Exception) -> str:
    """Get a user-friendly error message."""
    if isinstance(error, AutoSubError):
        return error.user_message
    return f"An error occurred: {type(error).__name__}"
