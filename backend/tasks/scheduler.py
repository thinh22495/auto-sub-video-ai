"""
Celery Beat periodic tasks for housekeeping.

Tasks:
- cleanup_temp_files: Remove old temp files
- cleanup_old_jobs: Archive/delete old completed jobs
- update_batch_statuses: Sync batch status from job states
- health_check: Periodic health verification
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.config.settings import settings
from backend.db.database import SessionLocal
from backend.db.models import Batch, Job
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------- Celery Beat Schedule ----------

celery_app.conf.beat_schedule = {
    "cleanup-temp-files": {
        "task": "backend.tasks.scheduler.cleanup_temp_files",
        "schedule": 3600.0,  # every hour
    },
    "cleanup-old-jobs": {
        "task": "backend.tasks.scheduler.cleanup_old_jobs",
        "schedule": 86400.0,  # daily
    },
    "update-batch-statuses": {
        "task": "backend.tasks.scheduler.update_batch_statuses",
        "schedule": 30.0,  # every 30 seconds
    },
    "health-check": {
        "task": "backend.tasks.scheduler.periodic_health_check",
        "schedule": 300.0,  # every 5 minutes
    },
}


# ---------- Tasks ----------

@celery_app.task(name="backend.tasks.scheduler.cleanup_temp_files")
def cleanup_temp_files():
    """Remove temporary files older than configured max age."""
    temp_dir = Path(settings.TEMP_DIR)
    if not temp_dir.exists():
        return {"cleaned": 0}

    max_age_seconds = settings.TEMP_FILE_MAX_AGE_HOURS * 3600
    now = time.time()
    cleaned = 0

    for path in temp_dir.iterdir():
        try:
            if path.is_file():
                age = now - path.stat().st_mtime
                if age > max_age_seconds:
                    path.unlink()
                    cleaned += 1
                    logger.debug("Cleaned temp file: %s (age: %.0fh)", path.name, age / 3600)
        except OSError as e:
            logger.warning("Failed to clean temp file %s: %s", path, e)

    if cleaned > 0:
        logger.info("Cleaned %d temp files", cleaned)

    return {"cleaned": cleaned}


@celery_app.task(name="backend.tasks.scheduler.cleanup_old_jobs")
def cleanup_old_jobs():
    """Delete completed jobs older than retention period."""
    retention_days = settings.COMPLETED_JOB_RETENTION_DAYS
    if retention_days <= 0:
        return {"deleted": 0}

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    db = SessionLocal()
    deleted = 0

    try:
        old_jobs = (
            db.query(Job)
            .filter(
                Job.status.in_(["COMPLETED", "FAILED", "CANCELLED"]),
                Job.completed_at < cutoff,
            )
            .all()
        )

        for job in old_jobs:
            _cleanup_job_files(job)
            db.delete(job)
            deleted += 1

        if deleted > 0:
            db.commit()
            logger.info("Cleaned %d old jobs (older than %d days)", deleted, retention_days)

        # Also clean up empty batches
        empty_batches = (
            db.query(Batch)
            .outerjoin(Job, Job.batch_id == Batch.id)
            .filter(Job.id.is_(None))
            .all()
        )
        for batch in empty_batches:
            db.delete(batch)
        if empty_batches:
            db.commit()
            logger.info("Cleaned %d empty batches", len(empty_batches))

    except Exception as e:
        logger.error("Error cleaning old jobs: %s", e)
        db.rollback()
    finally:
        db.close()

    return {"deleted": deleted}


@celery_app.task(name="backend.tasks.scheduler.update_batch_statuses")
def update_batch_statuses():
    """Sync batch statuses from their jobs. Handles race conditions."""
    db = SessionLocal()
    updated = 0

    try:
        active_batches = (
            db.query(Batch)
            .filter(Batch.status.in_(["QUEUED", "PROCESSING"]))
            .all()
        )

        for batch in active_batches:
            jobs = db.query(Job).filter(Job.batch_id == batch.id).all()
            if not jobs:
                continue

            completed = sum(1 for j in jobs if j.status == "COMPLETED")
            failed = sum(1 for j in jobs if j.status == "FAILED")
            cancelled = sum(1 for j in jobs if j.status == "CANCELLED")
            total = len(jobs)

            old_status = batch.status
            batch.completed_jobs = completed
            batch.failed_jobs = failed

            if completed + failed + cancelled >= total:
                batch.status = "COMPLETED" if failed == 0 and cancelled == 0 else "PARTIAL"
                batch.completed_at = datetime.now(timezone.utc)
            elif any(j.status == "PROCESSING" for j in jobs):
                batch.status = "PROCESSING"

            if batch.status != old_status:
                updated += 1

        if updated > 0:
            db.commit()

    except Exception as e:
        logger.error("Error updating batch statuses: %s", e)
        db.rollback()
    finally:
        db.close()

    return {"updated": updated}


@celery_app.task(name="backend.tasks.scheduler.periodic_health_check")
def periodic_health_check():
    """Periodic health check — detect stale jobs and log system status."""
    db = SessionLocal()
    stale_jobs = []
    issues = []

    try:
        # Find stale processing jobs (stuck for >1 hour)
        stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        stale_jobs = (
            db.query(Job)
            .filter(
                Job.status == "PROCESSING",
                Job.started_at < stale_cutoff,
            )
            .all()
        )

        for job in stale_jobs:
            issues.append(f"Stale job: {job.id} ({job.input_filename})")
            logger.warning(
                "Stale job detected: %s (%s), started at %s",
                job.id, job.input_filename, job.started_at,
            )

        # Check disk space
        import shutil
        for dir_path, dir_name in [
            (settings.VIDEO_INPUT_DIR, "Videos"),
            (settings.MODEL_DIR, "Models"),
            (settings.SUBTITLE_OUTPUT_DIR, "Subtitles"),
        ]:
            try:
                usage = shutil.disk_usage(dir_path)
                free_gb = usage.free / (1024**3)
                if free_gb < 1.0:
                    issues.append(f"Low disk space: {dir_name} ({free_gb:.1f}GB free)")
                    logger.warning("Low disk space on %s: %.1fGB free", dir_name, free_gb)
            except OSError:
                pass

    except Exception as e:
        logger.error("Health check error: %s", e)
    finally:
        db.close()

    return {"issues": issues, "stale_jobs": len(stale_jobs)}


# ---------- Helpers ----------

def _cleanup_job_files(job: Job):
    """Remove output files for a job."""
    import json

    if job.output_subtitle_paths:
        try:
            paths = json.loads(job.output_subtitle_paths)
            for p in paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except OSError:
                    pass
        except (json.JSONDecodeError, TypeError):
            pass

    if job.output_video_path:
        try:
            Path(job.output_video_path).unlink(missing_ok=True)
        except OSError:
            pass
