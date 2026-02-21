import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Bảng công việc - lưu trữ thông tin các tác vụ tạo phụ đề
class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    batch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("batches.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="QUEUED")
    input_path: Mapped[str] = mapped_column(String, nullable=False)
    input_filename: Mapped[str] = mapped_column(String, nullable=False)
    source_language: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_language: Mapped[str | None] = mapped_column(String, nullable=True)
    target_language: Mapped[str | None] = mapped_column(String, nullable=True)
    output_formats: Mapped[str] = mapped_column(Text, nullable=False)  # Mảng JSON
    burn_in: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_diarization: Mapped[bool] = mapped_column(Boolean, default=False)
    whisper_model: Mapped[str] = mapped_column(String, nullable=False)
    ollama_model: Mapped[str | None] = mapped_column(String, nullable=True)
    subtitle_style: Mapped[str | None] = mapped_column(Text, nullable=True)  # Kiểu JSON
    video_preset: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String, nullable=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    output_subtitle_paths: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Mảng JSON
    output_video_path: Mapped[str | None] = mapped_column(String, nullable=True)

    batch: Mapped["Batch | None"] = relationship(back_populates="jobs")
    versions: Mapped[list["SubtitleVersion"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


# Bảng nhóm xử lý hàng loạt - quản lý nhiều công việc cùng lúc
class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="QUEUED")
    total_jobs: Mapped[int] = mapped_column(Integer, default=0)
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    failed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    jobs: Mapped[list["Job"]] = relationship(back_populates="batch")


# Bảng phiên bản phụ đề - lưu trữ các phiên bản chỉnh sửa phụ đề
class SubtitleVersion(Base):
    __tablename__ = "subtitle_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String, ForeignKey("jobs.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="versions")


# Bảng mẫu cấu hình - lưu các thiết lập phụ đề và video có sẵn
class Preset(Base):
    __tablename__ = "presets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtitle_style: Mapped[str] = mapped_column(Text, nullable=False)  # Kiểu JSON
    video_settings: Mapped[str | None] = mapped_column(Text, nullable=True)  # Kiểu JSON
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# Bảng cài đặt ứng dụng - lưu các thiết lập cấu hình hệ thống
class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
