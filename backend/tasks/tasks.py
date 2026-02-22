from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from backend.config.settings import settings
from backend.db.database import SessionLocal
from backend.db.crud import get_job, update_job
from backend.tasks.callbacks import (
    clear_job_progress,
    create_progress_callback,
    publish_job_progress,
)
from backend.tasks.celery_app import celery_app
from backend.core.segment import ProgressInfo

logger = logging.getLogger(__name__)


@celery_app.task(
    name="backend.tasks.tasks.run_pipeline",
    bind=True,
    acks_late=True,
    max_retries=1,
    default_retry_delay=30,
)
def run_pipeline(self, job_id: str):
    """
    Chạy toàn bộ pipeline phụ đề cho một công việc.

    Đây là tác vụ chính điều phối tất cả các bước pipeline.
    Mỗi bước báo cáo tiến trình qua Redis pub/sub -> WebSocket.
    """
    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            logger.error("Không tìm thấy công việc: %s", job_id)
            return

        if job.status == "CANCELLED":
            logger.info("Công việc đã bị hủy, bỏ qua: %s", job_id)
            return

        # Đánh dấu đang xử lý
        update_job(
            db, job_id,
            status="PROCESSING",
            started_at=datetime.now(timezone.utc),
            current_step="Đang khởi tạo",
            progress_percent=0,
        )

        # Tạo callback tiến trình cập nhật cả Redis và DB
        progress_cb = create_progress_callback(job_id)

        def on_progress(progress: ProgressInfo):
            progress_cb(progress)
            # Cập nhật DB định kỳ (không phải mỗi callback để giảm ghi)
            if int(progress.progress_percent) % 5 == 0:
                try:
                    update_job(
                        db, job_id,
                        current_step=progress.step,
                        progress_percent=progress.progress_percent,
                    )
                except Exception:
                    pass

        # Phân tích tham số công việc
        output_formats = json.loads(job.output_formats) if isinstance(job.output_formats, str) else job.output_formats
        subtitle_style = json.loads(job.subtitle_style) if job.subtitle_style else None

        # Chạy pipeline
        from backend.core.pipeline import SubtitlePipeline

        pipeline = SubtitlePipeline(
            input_path=job.input_path,
            source_language=job.source_language,
            target_language=job.target_language,
            output_formats=output_formats,
            burn_in=job.burn_in,
            enable_diarization=job.enable_diarization,
            whisper_model=job.whisper_model,
            ollama_model=job.ollama_model,
            subtitle_style=subtitle_style,
            video_preset=job.video_preset,
            db=db,
            on_progress=on_progress,
        )

        result = pipeline.run()

        # Cập nhật công việc với kết quả
        update_job(
            db, job_id,
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc),
            current_step="Completed",
            progress_percent=100,
            detected_language=result.get("detected_language"),
            output_subtitle_paths=json.dumps(result.get("subtitle_paths", [])),
            output_video_path=result.get("output_video_path"),
        )

        # Phát tiến trình cuối cùng
        publish_job_progress(
            job_id,
            ProgressInfo(
                step="Completed",
                step_number=pipeline.total_steps,
                total_steps=pipeline.total_steps,
                progress_percent=100,
                message=f"Hoàn tất! Đã tạo {len(result.get('subtitle_paths', []))} tệp phụ đề",
            ),
            status="COMPLETED",
        )

        logger.info(
            "Công việc hoàn tất: %s (%.1fs, %d đoạn, ngôn ngữ=%s)",
            job_id,
            result.get("elapsed_seconds", 0),
            result.get("segment_count", 0),
            result.get("detected_language", "?"),
        )

    except Exception as exc:
        logger.exception("Công việc thất bại: %s", job_id)

        error_msg = str(exc)[:500]
        try:
            update_job(
                db, job_id,
                status="FAILED",
                completed_at=datetime.now(timezone.utc),
                current_step="Failed",
                error_message=error_msg,
            )
        except Exception:
            pass

        publish_job_progress(
            job_id,
            ProgressInfo(
                step="Failed",
                step_number=0,
                total_steps=0,
                progress_percent=0,
                message=f"Lỗi: {error_msg}",
            ),
            status="FAILED",
        )

        # Thử lại với các lỗi tạm thời
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

    finally:
        clear_job_progress(job_id)
        db.close()


# Giữ các stub tác vụ riêng lẻ cho việc định tuyến hàng đợi chi tiết trong tương lai
@celery_app.task(name="backend.tasks.tasks.extract_audio")
def extract_audio(job_id: str):
    """Placeholder - trích xuất âm thanh được xử lý trong run_pipeline."""
    pass


@celery_app.task(name="backend.tasks.tasks.transcribe")
def transcribe(job_id: str):
    """Placeholder - phiên âm được xử lý trong run_pipeline."""
    pass


@celery_app.task(name="backend.tasks.tasks.diarize")
def diarize(job_id: str):
    """Placeholder - phân biệt người nói sẽ được triển khai trong Giai đoạn 6."""
    pass


@celery_app.task(name="backend.tasks.tasks.translate")
def translate(job_id: str):
    """Placeholder - dịch thuật sẽ được triển khai trong Giai đoạn 3."""
    pass


@celery_app.task(name="backend.tasks.tasks.generate_subtitles")
def generate_subtitles(job_id: str):
    """Placeholder - tạo phụ đề được xử lý trong run_pipeline."""
    pass


@celery_app.task(name="backend.tasks.tasks.burn_in_subtitles")
def burn_in_subtitles(job_id: str):
    """Placeholder - ghi phụ đề vào video được xử lý trong run_pipeline."""
    pass


@celery_app.task(
    name="backend.tasks.tasks.download_whisper_model",
    bind=True,
    acks_late=True,
    max_retries=0,
)
def download_whisper_model(self, model_name: str):
    """
    Tải mô hình Whisper trong background.
    Tiến trình được phát qua Redis pub/sub -> WebSocket.
    """
    task_id = self.request.id
    _publish_model_download_progress(task_id, model_name, "downloading", 0, "Đang bắt đầu tải mô hình...")

    try:
        from backend.models.whisper_manager import WHISPER_MODELS, download_model

        if model_name not in WHISPER_MODELS:
            raise ValueError(f"Mô hình không xác định: {model_name}")

        _publish_model_download_progress(task_id, model_name, "downloading", 10, f"Đang tải mô hình {model_name}...")

        result = download_model(model_name)

        _publish_model_download_progress(task_id, model_name, "completed", 100, f"Đã tải xong mô hình {model_name}")

        return {
            "task_id": task_id,
            "model_name": model_name,
            "status": "completed",
            **result,
        }

    except Exception as exc:
        error_msg = str(exc)[:500]
        logger.exception("Tải mô hình thất bại: %s", model_name)
        _publish_model_download_progress(task_id, model_name, "failed", 0, f"Lỗi: {error_msg}")
        raise


def _publish_model_download_progress(task_id: str, model_name: str, status: str, progress: float, message: str):
    """Phát tiến trình tải mô hình qua Redis pub/sub."""
    try:
        import redis as sync_redis
        r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
        data = json.dumps({
            "task_id": task_id,
            "model_name": model_name,
            "status": status,
            "progress_percent": progress,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        r.publish(f"model_download:{task_id}", data)
        r.set(f"model_download:{task_id}:latest", data, ex=3600)
        r.close()
    except Exception as e:
        logger.warning("Không thể phát tiến trình tải mô hình: %s", e)
