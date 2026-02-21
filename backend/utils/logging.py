"""Cấu hình ghi log có cấu trúc cho AutoSubAI."""

import logging
import sys
from typing import Optional

from backend.config.settings import settings

# Định dạng log với ngữ cảnh có cấu trúc
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: Optional[str] = None) -> None:
    """Cấu hình ghi log cho ứng dụng."""
    log_level = level or ("DEBUG" if settings.DEBUG else "INFO")

    root = logging.getLogger()
    root.setLevel(log_level)

    # Xóa các handler hiện có
    root.handlers.clear()

    # Handler xuất ra console
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(handler)

    # Giảm log nhiễu từ các thư viện bên thứ ba
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("faster_whisper").setLevel(logging.INFO)
    logging.getLogger("celery").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Lấy logger theo tên."""
    return logging.getLogger(name)


class JobLogger:
    """Logger tự động đính kèm ngữ cảnh công việc vào các thông điệp."""

    def __init__(self, job_id: str, logger_name: str = "pipeline"):
        self._logger = logging.getLogger(logger_name)
        self._job_id = job_id

    def _fmt(self, msg: str) -> str:
        return f"[job:{self._job_id[:8]}] {msg}"

    def info(self, msg: str) -> None:
        self._logger.info(self._fmt(msg))

    def warning(self, msg: str) -> None:
        self._logger.warning(self._fmt(msg))

    def error(self, msg: str, exc_info: bool = False) -> None:
        self._logger.error(self._fmt(msg), exc_info=exc_info)

    def debug(self, msg: str) -> None:
        self._logger.debug(self._fmt(msg))
