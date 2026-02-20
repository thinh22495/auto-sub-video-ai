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
    Run the full subtitle pipeline for a job.

    This is the main task that orchestrates all pipeline steps.
    Each step reports progress via Redis pub/sub -> WebSocket.
    """
    db = SessionLocal()
    try:
        job = get_job(db, job_id)
        if not job:
            logger.error("Job not found: %s", job_id)
            return

        if job.status == "CANCELLED":
            logger.info("Job was cancelled, skipping: %s", job_id)
            return

        # Mark as processing
        update_job(
            db, job_id,
            status="PROCESSING",
            started_at=datetime.now(timezone.utc),
            current_step="Initializing",
            progress_percent=0,
        )

        # Create progress callback that updates both Redis and DB
        progress_cb = create_progress_callback(job_id)

        def on_progress(progress: ProgressInfo):
            progress_cb(progress)
            # Also update DB periodically (not every callback to reduce writes)
            if int(progress.progress_percent) % 5 == 0:
                try:
                    update_job(
                        db, job_id,
                        current_step=progress.step,
                        progress_percent=progress.progress_percent,
                    )
                except Exception:
                    pass

        # Parse job parameters
        output_formats = json.loads(job.output_formats) if isinstance(job.output_formats, str) else job.output_formats
        subtitle_style = json.loads(job.subtitle_style) if job.subtitle_style else None

        # Run the pipeline
        from backend.core.pipeline import SubtitlePipeline

        pipeline = SubtitlePipeline(
            input_path=job.input_path,
            source_language=job.source_language,
            target_language=job.target_language,
            output_formats=output_formats,
            burn_in=job.burn_in,
            whisper_model=job.whisper_model,
            ollama_model=job.ollama_model,
            subtitle_style=subtitle_style,
            on_progress=on_progress,
        )

        result = pipeline.run()

        # Update job with results
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

        # Publish final progress
        publish_job_progress(
            job_id,
            ProgressInfo(
                step="Completed",
                step_number=pipeline.total_steps,
                total_steps=pipeline.total_steps,
                progress_percent=100,
                message=f"Done! Generated {len(result.get('subtitle_paths', []))} subtitle file(s)",
            ),
            status="COMPLETED",
        )

        logger.info(
            "Job completed: %s (%.1fs, %d segments, language=%s)",
            job_id,
            result.get("elapsed_seconds", 0),
            result.get("segment_count", 0),
            result.get("detected_language", "?"),
        )

    except Exception as exc:
        logger.exception("Job failed: %s", job_id)

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
                message=f"Error: {error_msg}",
            ),
            status="FAILED",
        )

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)

    finally:
        clear_job_progress(job_id)
        db.close()


# Keep individual task stubs for future fine-grained queue routing
@celery_app.task(name="backend.tasks.tasks.extract_audio")
def extract_audio(job_id: str):
    """Placeholder - audio extraction is handled within run_pipeline."""
    pass


@celery_app.task(name="backend.tasks.tasks.transcribe")
def transcribe(job_id: str):
    """Placeholder - transcription is handled within run_pipeline."""
    pass


@celery_app.task(name="backend.tasks.tasks.diarize")
def diarize(job_id: str):
    """Placeholder - diarization will be implemented in Phase 6."""
    pass


@celery_app.task(name="backend.tasks.tasks.translate")
def translate(job_id: str):
    """Placeholder - translation will be implemented in Phase 3."""
    pass


@celery_app.task(name="backend.tasks.tasks.generate_subtitles")
def generate_subtitles(job_id: str):
    """Placeholder - subtitle generation is handled within run_pipeline."""
    pass


@celery_app.task(name="backend.tasks.tasks.burn_in_subtitles")
def burn_in_subtitles(job_id: str):
    """Placeholder - burn-in is handled within run_pipeline."""
    pass
