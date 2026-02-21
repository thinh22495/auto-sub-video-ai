from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db import crud
from backend.db.models import SubtitleVersion
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


# ---------- Subtitle Editing ----------

class SubtitleSegment(BaseModel):
    index: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    translated_text: Optional[str] = None


class SubtitleUpdateRequest(BaseModel):
    segments: list[SubtitleSegment]
    format: str = "srt"
    description: Optional[str] = None


class SubtitleVersionResponse(BaseModel):
    id: str
    version: int
    format: str
    created_at: str
    description: Optional[str]


@router.get("/{job_id}/subtitles/parsed")
def get_parsed_subtitles(job_id: str, db: Session = Depends(get_db)):
    """Get subtitle segments as structured data for editor."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    paths = json.loads(job.output_subtitle_paths) if job.output_subtitle_paths else []
    if not paths:
        raise HTTPException(status_code=404, detail="No subtitle files found")

    # Prefer SRT for parsing, fallback to first available
    target_path = paths[0]
    for p in paths:
        if p.endswith(".srt"):
            target_path = p
            break

    path = Path(target_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Subtitle file not found on disk")

    segments = _parse_subtitle_file(str(path))
    return {
        "job_id": job_id,
        "format": path.suffix.lstrip("."),
        "source_path": str(path),
        "segments": segments,
    }


@router.put("/{job_id}/subtitles")
def update_subtitles(job_id: str, req: SubtitleUpdateRequest, db: Session = Depends(get_db)):
    """Update subtitles with edited segments. Creates a new version."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    # Generate subtitle content from segments
    content = _generate_subtitle_content(req.segments, req.format)

    # Determine version number
    existing_versions = (
        db.query(SubtitleVersion)
        .filter(SubtitleVersion.job_id == job_id)
        .order_by(SubtitleVersion.version.desc())
        .first()
    )
    next_version = (existing_versions.version + 1) if existing_versions else 1

    # Save version to DB
    version = SubtitleVersion(
        job_id=job_id,
        version=next_version,
        format=req.format,
        content=content,
        description=req.description or f"Edit v{next_version}",
    )
    db.add(version)

    # Also write to disk (overwrite the original file)
    paths = json.loads(job.output_subtitle_paths) if job.output_subtitle_paths else []
    for p in paths:
        if p.endswith(f".{req.format}"):
            Path(p).write_text(content, encoding="utf-8")
            break
    else:
        # If no matching format found, write as new file
        output_dir = Path(settings.SUBTITLE_OUTPUT_DIR)
        new_path = str(output_dir / f"{Path(job.input_path).stem}.{req.format}")
        Path(new_path).write_text(content, encoding="utf-8")
        paths.append(new_path)
        crud.update_job(db, job_id, output_subtitle_paths=json.dumps(paths))

    db.commit()

    return {
        "version": next_version,
        "format": req.format,
        "segment_count": len(req.segments),
        "message": f"Subtitles updated (v{next_version})",
    }


@router.get("/{job_id}/subtitles/versions")
def list_subtitle_versions(job_id: str, db: Session = Depends(get_db)):
    """List all saved versions of subtitles for a job."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    versions = (
        db.query(SubtitleVersion)
        .filter(SubtitleVersion.job_id == job_id)
        .order_by(SubtitleVersion.version.desc())
        .all()
    )

    return [
        {
            "id": v.id,
            "version": v.version,
            "format": v.format,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "description": v.description,
        }
        for v in versions
    ]


@router.get("/{job_id}/subtitles/versions/{version_id}")
def get_subtitle_version(job_id: str, version_id: str, db: Session = Depends(get_db)):
    """Get a specific subtitle version content."""
    version = (
        db.query(SubtitleVersion)
        .filter(SubtitleVersion.id == version_id, SubtitleVersion.job_id == job_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    segments = _parse_subtitle_content(version.content, version.format)
    return {
        "id": version.id,
        "version": version.version,
        "format": version.format,
        "content": version.content,
        "segments": segments,
        "created_at": version.created_at.isoformat() if version.created_at else None,
        "description": version.description,
    }


@router.post("/{job_id}/subtitles/versions/{version_id}/restore")
def restore_subtitle_version(job_id: str, version_id: str, db: Session = Depends(get_db)):
    """Restore a previous subtitle version."""
    version = (
        db.query(SubtitleVersion)
        .filter(SubtitleVersion.id == version_id, SubtitleVersion.job_id == job_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    job = crud.get_job(db, job_id)
    paths = json.loads(job.output_subtitle_paths) if job.output_subtitle_paths else []

    # Write restored content to disk
    for p in paths:
        if p.endswith(f".{version.format}"):
            Path(p).write_text(version.content, encoding="utf-8")
            break

    return {"message": f"Restored version {version.version}", "version": version.version}


@router.get("/{job_id}/audio")
def stream_audio(job_id: str, db: Session = Depends(get_db)):
    """Stream extracted audio for waveform display in editor."""
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for cached audio file
    temp_dir = Path(settings.TEMP_DIR)
    input_stem = Path(job.input_path).stem
    audio_path = temp_dir / f"{input_stem}_{job_id[:8]}.wav"

    if not audio_path.exists():
        # Extract audio on-demand
        from backend.video.ffmpeg_wrapper import extract_audio
        extracted = extract_audio(job.input_path)
        # Move to predictable location
        import shutil
        shutil.move(extracted, str(audio_path))

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Could not extract audio")

    def iterfile():
        with open(audio_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="audio/wav",
        headers={"Content-Disposition": f"inline; filename={audio_path.name}"},
    )


# ---------- Helpers ----------

def _parse_subtitle_file(path: str) -> list[dict]:
    """Parse a subtitle file into structured segments."""
    content = Path(path).read_text(encoding="utf-8")
    fmt = Path(path).suffix.lstrip(".")
    return _parse_subtitle_content(content, fmt)


def _parse_subtitle_content(content: str, fmt: str) -> list[dict]:
    """Parse subtitle content string into segments."""
    if fmt == "srt":
        return _parse_srt(content)
    elif fmt == "vtt":
        return _parse_vtt(content)
    elif fmt == "ass":
        return _parse_ass(content)
    return []


def _parse_srt(content: str) -> list[dict]:
    """Parse SRT content into segments."""
    import re
    segments = []
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # Parse index
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # Parse timestamps
        ts_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            lines[1].strip(),
        )
        if not ts_match:
            continue

        start = _srt_ts_to_seconds(ts_match.group(1))
        end = _srt_ts_to_seconds(ts_match.group(2))

        # Parse text (may be multiple lines)
        text = "\n".join(lines[2:]).strip()

        # Extract speaker if present: [Speaker 1]: text
        speaker = None
        speaker_match = re.match(r"\[([^\]]+)\]:\s*(.*)", text, re.DOTALL)
        if speaker_match:
            speaker = speaker_match.group(1)
            text = speaker_match.group(2)

        segments.append({
            "index": index,
            "start": start,
            "end": end,
            "text": text,
            "speaker": speaker,
        })

    return segments


def _parse_vtt(content: str) -> list[dict]:
    """Parse VTT content into segments."""
    import re
    segments = []
    # Remove WEBVTT header
    content = re.sub(r"^WEBVTT[^\n]*\n\n?", "", content, flags=re.MULTILINE)
    blocks = re.split(r"\n\s*\n", content.strip())

    idx = 1
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue

        # Find timestamp line
        ts_line_idx = 0
        for i, line in enumerate(lines):
            if "-->" in line:
                ts_line_idx = i
                break
        else:
            continue

        ts_match = re.match(
            r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})",
            lines[ts_line_idx].strip(),
        )
        if not ts_match:
            continue

        start = _vtt_ts_to_seconds(ts_match.group(1))
        end = _vtt_ts_to_seconds(ts_match.group(2))
        text = "\n".join(lines[ts_line_idx + 1:]).strip()

        segments.append({
            "index": idx,
            "start": start,
            "end": end,
            "text": text,
            "speaker": None,
        })
        idx += 1

    return segments


def _parse_ass(content: str) -> list[dict]:
    """Parse ASS content into segments (dialogue events only)."""
    import re
    segments = []
    idx = 1

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("Dialogue:"):
            continue

        # Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        parts = line[len("Dialogue:"):].split(",", 9)
        if len(parts) < 10:
            continue

        start = _ass_ts_to_seconds(parts[1].strip())
        end = _ass_ts_to_seconds(parts[2].strip())
        speaker = parts[4].strip() or None
        text = parts[9].strip()

        # Remove ASS override tags
        text = re.sub(r"\{[^}]*\}", "", text)
        # Replace \N with newline
        text = text.replace("\\N", "\n")

        segments.append({
            "index": idx,
            "start": start,
            "end": end,
            "text": text,
            "speaker": speaker,
        })
        idx += 1

    return segments


def _srt_ts_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _vtt_ts_to_seconds(ts: str) -> float:
    parts = ts.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _ass_ts_to_seconds(ts: str) -> float:
    parts = ts.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _generate_subtitle_content(segments: list[SubtitleSegment], fmt: str) -> str:
    """Generate subtitle file content from segments."""
    if fmt == "srt":
        return _generate_srt(segments)
    elif fmt == "vtt":
        return _generate_vtt(segments)
    raise HTTPException(status_code=400, detail=f"Editing format '{fmt}' not supported. Use srt or vtt.")


def _generate_srt(segments: list[SubtitleSegment]) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        start_ts = _seconds_to_srt_ts(seg.start)
        end_ts = _seconds_to_srt_ts(seg.end)
        text = seg.text
        if seg.speaker:
            text = f"[{seg.speaker}]: {text}"
        lines.append(f"{i}\n{start_ts} --> {end_ts}\n{text}\n")
    return "\n".join(lines)


def _generate_vtt(segments: list[SubtitleSegment]) -> str:
    lines = ["WEBVTT\n"]
    for i, seg in enumerate(segments, 1):
        start_ts = _seconds_to_vtt_ts(seg.start)
        end_ts = _seconds_to_vtt_ts(seg.end)
        text = seg.text
        if seg.speaker:
            text = f"<v {seg.speaker}>{text}"
        lines.append(f"{i}\n{start_ts} --> {end_ts}\n{text}\n")
    return "\n".join(lines)


def _seconds_to_srt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _seconds_to_vtt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
