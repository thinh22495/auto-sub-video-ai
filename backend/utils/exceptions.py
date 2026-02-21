"""Error classification and exception types for AutoSubAI.

Errors are classified as:
- Transient: temporary failures that may succeed on retry (network, resource contention)
- Permanent: failures that will not resolve without user intervention (bad input, missing model)
"""

from enum import Enum


class ErrorCategory(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class AutoSubError(Exception):
    """Base exception for AutoSubAI."""

    category: ErrorCategory = ErrorCategory.PERMANENT
    user_message: str = "An unexpected error occurred."

    def __init__(self, message: str, user_message: str | None = None):
        super().__init__(message)
        if user_message:
            self.user_message = user_message


# --- Transient errors (auto-retry candidates) ---


class TransientError(AutoSubError):
    """Base for errors that may succeed on retry."""

    category = ErrorCategory.TRANSIENT


class OllamaConnectionError(TransientError):
    """Ollama server unreachable."""

    user_message = "Translation service temporarily unavailable. Will retry."


class RedisConnectionError(TransientError):
    """Redis connection failed."""

    user_message = "Task queue temporarily unavailable."


class GPUMemoryError(TransientError):
    """GPU out of memory — may free up after other tasks complete."""

    user_message = "GPU memory full. Job will retry when resources are available."


class ResourceBusyError(TransientError):
    """Resource locked by another process."""

    user_message = "System resources are busy. Will retry shortly."


# --- Permanent errors (need user action) ---


class PermanentError(AutoSubError):
    """Base for errors that won't resolve without user intervention."""

    category = ErrorCategory.PERMANENT


class FileNotFoundError(PermanentError):
    """Input file doesn't exist."""

    user_message = "The specified file was not found."


class InvalidFileError(PermanentError):
    """File format unsupported or corrupt."""

    user_message = "The file is not a supported video format or is corrupted."


class ModelNotFoundError(PermanentError):
    """Required AI model not downloaded."""

    user_message = "Required model is not available. Please download it first."


class TranscriptionError(PermanentError):
    """Whisper failed to process audio."""

    user_message = "Failed to transcribe audio. The file may be corrupted or contain no speech."


class TranslationError(PermanentError):
    """Ollama translation produced bad output."""

    user_message = "Translation failed. Try a different model or language pair."


class FFmpegError(PermanentError):
    """FFmpeg processing failed."""

    user_message = "Video processing failed. The file may be corrupted or use an unsupported codec."


class SecurityError(PermanentError):
    """Path traversal or other security violation."""

    user_message = "Access denied: invalid file path."


# --- Classification helpers ---

# Substrings in error messages that indicate transient failures
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
    """Classify an arbitrary exception as transient or permanent."""
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
