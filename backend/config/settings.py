from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AUTOSUB_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Máy chủ
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Đường dẫn
    VIDEO_INPUT_DIR: str = "/data/videos"
    SUBTITLE_OUTPUT_DIR: str = "/data/subtitles"
    VIDEO_OUTPUT_DIR: str = "/data/output"
    MODEL_DIR: str = "/data/models"
    DB_PATH: str = "/data/db/autosub.db"
    TEMP_DIR: str = "/tmp/autosub"

    # Mô hình AI
    DEFAULT_WHISPER_MODEL: str = "large-v3-turbo"
    DEFAULT_OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_BASE_URL: str = "http://autosub-ollama:11434"
    WHISPER_DEVICE: str = "auto"  # tự động, cuda, cpu
    WHISPER_COMPUTE_TYPE: str = "auto"  # tự động, float16, int8, float32

    # Xử lý
    MAX_CONCURRENT_JOBS: int = 2
    GPU_WORKER_CONCURRENCY: int = 1
    CPU_WORKER_CONCURRENCY: int = 4
    MAX_UPLOAD_SIZE_MB: int = 10000

    # Kết nối Redis
    REDIS_URL: str = "redis://autosub-redis:6379/0"

    # Cấu hình phụ đề mặc định
    DEFAULT_SUBTITLE_FORMAT: str = "srt"
    DEFAULT_MAX_LINE_LENGTH: int = 42
    DEFAULT_MAX_LINES: int = 2

    # Dọn dẹp
    TEMP_FILE_MAX_AGE_HOURS: int = 24
    COMPLETED_JOB_RETENTION_DAYS: int = 30

    def ensure_directories(self) -> None:
        for dir_path in [
            self.VIDEO_INPUT_DIR,
            self.SUBTITLE_OUTPUT_DIR,
            self.VIDEO_OUTPUT_DIR,
            self.MODEL_DIR,
            self.TEMP_DIR,
            str(Path(self.DB_PATH).parent),
        ]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


settings = Settings()
