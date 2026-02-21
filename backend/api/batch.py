from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db import crud
from backend.db.models import Batch, Job
from backend.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


# ---------- Lược đồ Pydantic ----------

class BatchFileConfig(BaseModel):
    """Cấu hình ghi đè cho từng file trong một batch."""
    input_path: str
    source_language: Optional[str] = None  # ghi đè cấu hình chung


class BatchCreateRequest(BaseModel):
    name: Optional[str] = None
    files: list[BatchFileConfig] = Field(..., min_length=1)
    # Cấu hình chung áp dụng cho tất cả file
    target_language: Optional[str] = None
    output_formats: list[str] = Field(default=["srt"])
    burn_in: bool = False
    enable_diarization: bool = False
    whisper_model: str = "large-v3-turbo"
    ollama_model: Optional[str] = None
    subtitle_style: Optional[dict] = None
    video_preset: Optional[str] = None
    priority: int = 0


class BatchResponse(BaseModel):
    id: str
    name: Optional[str]
    status: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    created_at: str
    completed_at: Optional[str]
    jobs: list[dict] = []


# ---------- Hàm hỗ trợ ----------

def _batch_to_response(batch: Batch, include_jobs: bool = False, db: Session | None = None) -> dict:
    result = {
        "id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "total_jobs": batch.total_jobs,
        "completed_jobs": batch.completed_jobs,
        "failed_jobs": batch.failed_jobs,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
        "jobs": [],
    }

    if include_jobs and db:
        jobs = db.query(Job).filter(Job.batch_id == batch.id).order_by(Job.created_at).all()
        result["jobs"] = [_job_summary(j) for j in jobs]

    return result


def _job_summary(job: Job) -> dict:
    def _parse_json(val):
        if val is None:
            return None
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        return val

    return {
        "id": job.id,
        "status": job.status,
        "input_filename": job.input_filename,
        "current_step": job.current_step,
        "progress_percent": job.progress_percent or 0,
        "error_message": job.error_message,
        "output_subtitle_paths": _parse_json(job.output_subtitle_paths),
        "output_video_path": job.output_video_path,
    }


def _update_batch_status(db: Session, batch_id: str):
    """Tính lại trạng thái batch từ các công việc của nó."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return

    jobs = db.query(Job).filter(Job.batch_id == batch_id).all()
    completed = sum(1 for j in jobs if j.status == "COMPLETED")
    failed = sum(1 for j in jobs if j.status == "FAILED")
    cancelled = sum(1 for j in jobs if j.status == "CANCELLED")
    total = len(jobs)

    batch.completed_jobs = completed
    batch.failed_jobs = failed

    if completed + failed + cancelled >= total:
        from datetime import datetime, timezone
        batch.status = "COMPLETED" if failed == 0 and cancelled == 0 else "PARTIAL"
        batch.completed_at = datetime.now(timezone.utc)
    elif any(j.status == "PROCESSING" for j in jobs):
        batch.status = "PROCESSING"
    else:
        batch.status = "QUEUED"

    db.commit()


# ---------- Các endpoint ----------

@router.post("", status_code=202)
def create_batch(req: BatchCreateRequest, db: Session = Depends(get_db)):
    """Tạo một batch các công việc tạo phụ đề."""
    # Kiểm tra các file
    valid_formats = {"srt", "ass", "vtt"}
    for fmt in req.output_formats:
        if fmt not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Invalid format: {fmt}")

    for fc in req.files:
        if not Path(fc.input_path).exists():
            raise HTTPException(status_code=400, detail=f"File not found: {fc.input_path}")

    # Tạo batch
    batch = Batch(
        name=req.name or f"Batch ({len(req.files)} files)",
        status="QUEUED",
        total_jobs=len(req.files),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Tạo công việc cho từng file
    job_ids = []
    for fc in req.files:
        input_file = Path(fc.input_path)
        job = Job(
            batch_id=batch.id,
            input_path=str(input_file),
            input_filename=input_file.name,
            source_language=fc.source_language,
            target_language=req.target_language,
            output_formats=json.dumps(req.output_formats),
            burn_in=req.burn_in,
            enable_diarization=req.enable_diarization,
            whisper_model=req.whisper_model,
            ollama_model=req.ollama_model,
            subtitle_style=json.dumps(req.subtitle_style) if req.subtitle_style else None,
            video_preset=req.video_preset,
            priority=req.priority,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_ids.append(job.id)

    # Gửi tất cả công việc đến Celery
    from backend.tasks.tasks import run_pipeline
    for jid in job_ids:
        run_pipeline.apply_async(args=[jid], priority=req.priority)

    logger.info("Batch created: %s (%d jobs)", batch.id, len(job_ids))

    return _batch_to_response(batch, include_jobs=True, db=db)


@router.get("")
def list_batches(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all batches."""
    batches = (
        db.query(Batch)
        .order_by(Batch.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_batch_to_response(b) for b in batches]


@router.get("/{batch_id}")
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    """Get batch details with all job statuses."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Recalculate status
    _update_batch_status(db, batch_id)
    db.refresh(batch)

    return _batch_to_response(batch, include_jobs=True, db=db)


@router.delete("/{batch_id}")
def delete_batch(batch_id: str, db: Session = Depends(get_db)):
    """Delete a batch and all its jobs."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Cancel any running jobs
    jobs = db.query(Job).filter(Job.batch_id == batch_id).all()
    for job in jobs:
        if job.status in ("QUEUED", "PROCESSING"):
            job.status = "CANCELLED"

    db.commit()

    # Delete all jobs then batch
    db.query(Job).filter(Job.batch_id == batch_id).delete()
    db.delete(batch)
    db.commit()

    return {"message": "Batch deleted", "id": batch_id}


@router.post("/{batch_id}/cancel")
def cancel_batch(batch_id: str, db: Session = Depends(get_db)):
    """Cancel all pending/processing jobs in a batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    cancelled = 0
    jobs = db.query(Job).filter(Job.batch_id == batch_id).all()
    for job in jobs:
        if job.status in ("QUEUED", "PROCESSING"):
            job.status = "CANCELLED"
            cancelled += 1

    db.commit()
    _update_batch_status(db, batch_id)

    return {"message": f"Cancelled {cancelled} jobs", "cancelled": cancelled}


@router.post("/{batch_id}/retry")
def retry_batch(batch_id: str, db: Session = Depends(get_db)):
    """Retry all failed jobs in a batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    retried = 0
    jobs = db.query(Job).filter(Job.batch_id == batch_id).all()
    from backend.tasks.tasks import run_pipeline

    for job in jobs:
        if job.status in ("FAILED", "CANCELLED"):
            job.status = "QUEUED"
            job.current_step = None
            job.progress_percent = 0
            job.error_message = None
            job.started_at = None
            job.completed_at = None
            retried += 1

    db.commit()

    # Re-dispatch
    for job in jobs:
        if job.status == "QUEUED":
            run_pipeline.apply_async(args=[job.id], priority=job.priority)

    _update_batch_status(db, batch_id)

    return {"message": f"Retried {retried} jobs", "retried": retried}


@router.get("/{batch_id}/progress")
def get_batch_progress(batch_id: str, db: Session = Depends(get_db)):
    """Get aggregate progress for a batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    jobs = db.query(Job).filter(Job.batch_id == batch_id).all()
    if not jobs:
        return {"overall_percent": 0, "jobs": []}

    total_progress = sum(j.progress_percent or 0 for j in jobs)
    overall = total_progress / len(jobs) if jobs else 0

    return {
        "batch_id": batch_id,
        "status": batch.status,
        "overall_percent": round(overall, 1),
        "total": len(jobs),
        "completed": sum(1 for j in jobs if j.status == "COMPLETED"),
        "failed": sum(1 for j in jobs if j.status == "FAILED"),
        "processing": sum(1 for j in jobs if j.status == "PROCESSING"),
        "queued": sum(1 for j in jobs if j.status == "QUEUED"),
        "jobs": [_job_summary(j) for j in jobs],
    }
