from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db import crud
from backend.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ---------- Pydantic Schemas ----------

class SubtitleStyleSchema(BaseModel):
    font_name: str = "Arial"
    font_size: int = 24
    primary_color: str = "#FFFFFF"
    secondary_color: str = "#FFFF00"
    outline_color: str = "#000000"
    shadow_color: str = "#000000"
    outline_width: float = 2.0
    shadow_depth: float = 1.0
    alignment: int = 2
    margin_left: int = 10
    margin_right: int = 10
    margin_vertical: int = 30
    bold: bool = False
    italic: bool = False
    max_line_length: int = 42
    max_lines: int = 2


class JobCreateRequest(BaseModel):
    input_path: str
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    output_formats: list[str] = Field(default=["srt"])
    burn_in: bool = False
    enable_diarization: bool = False
    whisper_model: str = Field(default="large-v3-turbo")
    ollama_model: Optional[str] = None
    subtitle_style: Optional[SubtitleStyleSchema] = None
    video_preset: Optional[str] = None
    priority: int = 0


class JobResponse(BaseModel):
    id: str
    status: str
    input_path: str
    input_filename: str
    source_language: Optional[str]
    detected_language: Optional[str]
    target_language: Optional[str]
    output_formats: list[str]
    burn_in: bool
    enable_diarization: bool
    whisper_model: str
    ollama_model: Optional[str]
    subtitle_style: Optional[dict]
    video_preset: Optional[str]
    priority: int
    current_step: Optional[str]
    progress_percent: float
    error_message: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    output_subtitle_paths: Optional[list[str]]
    output_video_path: Optional[str]

    class Config:
        from_attributes = True


def _job_to_response(job) -> dict:
    """Convert a Job ORM model to a response dict."""

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
        "input_path": job.input_path,
        "input_filename": job.input_filename,
        "source_language": job.source_language,
        "detected_language": job.detected_language,
        "target_language": job.target_language,
        "output_formats": _parse_json(job.output_formats) or [],
        "burn_in": job.burn_in,
        "enable_diarization": job.enable_diarization,
        "whisper_model": job.whisper_model,
        "ollama_model": job.ollama_model,
        "subtitle_style": _parse_json(job.subtitle_style),
        "video_preset": job.video_preset,
        "priority": job.priority,
        "current_step": job.current_step,
        "progress_percent": job.progress_percent or 0,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "output_subtitle_paths": _parse_json(job.output_subtitle_paths),
        "output_video_path": job.output_video_path,
    }


# ---------- Endpoints ----------

@router.post("", status_code=202)
def create_job(req: JobCreateRequest, db: Session = Depends(get_db)):
    """Create a new subtitle generation job."""
    # Validate input file exists
    input_file = Path(req.input_path)
    if not input_file.exists():
        raise HTTPException(status_code=400, detail=f"Input file not found: {req.input_path}")

    # Validate output formats
    valid_formats = {"srt", "ass", "vtt"}
    for fmt in req.output_formats:
        if fmt not in valid_formats:
            raise HTTPException(status_code=400, detail=f"Invalid format: {fmt}. Valid: {valid_formats}")

    # Create job in database
    job = crud.create_job(
        db,
        input_path=str(input_file),
        input_filename=input_file.name,
        source_language=req.source_language,
        target_language=req.target_language,
        output_formats=json.dumps(req.output_formats),
        burn_in=req.burn_in,
        enable_diarization=req.enable_diarization,
        whisper_model=req.whisper_model,
        ollama_model=req.ollama_model,
        subtitle_style=json.dumps(req.subtitle_style.model_dump()) if req.subtitle_style else None,
        video_preset=req.video_preset,
        priority=req.priority,
    )

    # Dispatch Celery task
    from backend.tasks.tasks import run_pipeline
    run_pipeline.apply_async(args=[job.id], priority=req.priority)

    logger.info("Job created: %s (%s)", job.id, input_file.name)

    return _job_to_response(job)


@router.get("")
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all jobs, optionally filtered by status."""
    jobs = crud.get_jobs(db, skip=skip, limit=limit, status=status)
    return [_job_to_response(j) for j in jobs]


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get details of a specific job."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.delete("/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel and delete a job."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # If still processing, mark as cancelled
    if job.status in ("QUEUED", "PROCESSING"):
        crud.update_job(db, job_id, status="CANCELLED")

    crud.delete_job(db, job_id)
    return {"message": "Job deleted", "id": job_id}


@router.post("/{job_id}/retry")
def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Retry a failed job."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("FAILED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Cannot retry job with status: {job.status}")

    crud.update_job(
        db, job_id,
        status="QUEUED",
        current_step=None,
        progress_percent=0,
        error_message=None,
        started_at=None,
        completed_at=None,
    )

    from backend.tasks.tasks import run_pipeline
    run_pipeline.apply_async(args=[job_id], priority=job.priority)

    return _job_to_response(crud.get_job(db, job_id))


@router.get("/{job_id}/subtitles")
def get_subtitles(job_id: str, db: Session = Depends(get_db)):
    """Get generated subtitle content."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    paths = json.loads(job.output_subtitle_paths) if job.output_subtitle_paths else []
    if not paths:
        raise HTTPException(status_code=404, detail="No subtitle files found")

    results = []
    for p in paths:
        path = Path(p)
        if path.exists():
            results.append({
                "path": str(path),
                "filename": path.name,
                "format": path.suffix.lstrip("."),
                "content": path.read_text(encoding="utf-8"),
            })

    return results


@router.get("/{job_id}/download")
def download_result(
    job_id: str,
    type: str = Query("subtitle", regex="^(subtitle|video)$"),
    format: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Download job result (subtitle file or video)."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if type == "video":
        if not job.output_video_path or not Path(job.output_video_path).exists():
            raise HTTPException(status_code=404, detail="Output video not found")
        return FileResponse(
            job.output_video_path,
            filename=Path(job.output_video_path).name,
            media_type="video/mp4",
        )

    # Subtitle download
    paths = json.loads(job.output_subtitle_paths) if job.output_subtitle_paths else []
    if not paths:
        raise HTTPException(status_code=404, detail="No subtitle files found")

    # Find the requested format or return first available
    target_path = None
    if format:
        for p in paths:
            if Path(p).suffix.lstrip(".") == format:
                target_path = p
                break
    if not target_path:
        target_path = paths[0]

    target = Path(target_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Subtitle file not found on disk")

    media_types = {
        ".srt": "text/plain",
        ".ass": "text/plain",
        ".vtt": "text/vtt",
    }

    return FileResponse(
        str(target),
        filename=target.name,
        media_type=media_types.get(target.suffix, "application/octet-stream"),
    )
