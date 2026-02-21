"""Application settings API endpoints."""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.db.database import get_db
from backend.db.crud import get_setting, set_setting

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


# Settings keys and their defaults (derived from settings.py)
SETTINGS_SCHEMA: dict[str, dict] = {
    "default_whisper_model": {
        "type": "select",
        "label": "Default Whisper Model",
        "description": "Speech-to-text model used for new jobs",
        "default": settings.DEFAULT_WHISPER_MODEL,
        "options": ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"],
        "category": "models",
    },
    "default_ollama_model": {
        "type": "text",
        "label": "Default Ollama Model",
        "description": "Translation model used by default (e.g. qwen2.5:7b)",
        "default": settings.DEFAULT_OLLAMA_MODEL,
        "category": "models",
    },
    "default_subtitle_format": {
        "type": "select",
        "label": "Default Subtitle Format",
        "description": "Default output format for new jobs",
        "default": settings.DEFAULT_SUBTITLE_FORMAT,
        "options": ["srt", "ass", "vtt"],
        "category": "subtitles",
    },
    "default_max_line_length": {
        "type": "number",
        "label": "Max Line Length",
        "description": "Maximum characters per subtitle line",
        "default": str(settings.DEFAULT_MAX_LINE_LENGTH),
        "min": 20,
        "max": 80,
        "category": "subtitles",
    },
    "default_max_lines": {
        "type": "number",
        "label": "Max Lines",
        "description": "Maximum number of lines per subtitle",
        "default": str(settings.DEFAULT_MAX_LINES),
        "min": 1,
        "max": 4,
        "category": "subtitles",
    },
    "max_concurrent_jobs": {
        "type": "number",
        "label": "Max Concurrent Jobs",
        "description": "Maximum jobs to process simultaneously",
        "default": str(settings.MAX_CONCURRENT_JOBS),
        "min": 1,
        "max": 10,
        "category": "processing",
    },
    "temp_file_max_age_hours": {
        "type": "number",
        "label": "Temp File Max Age (hours)",
        "description": "Auto-delete temp files older than this",
        "default": str(settings.TEMP_FILE_MAX_AGE_HOURS),
        "min": 1,
        "max": 168,
        "category": "cleanup",
    },
    "completed_job_retention_days": {
        "type": "number",
        "label": "Job Retention (days)",
        "description": "Keep completed job records for this many days",
        "default": str(settings.COMPLETED_JOB_RETENTION_DAYS),
        "min": 1,
        "max": 365,
        "category": "cleanup",
    },
}


# ---------- Schemas ----------

class SettingUpdate(BaseModel):
    key: str
    value: str


class SettingsBulkUpdate(BaseModel):
    settings: dict[str, str]


# ---------- Endpoints ----------

@router.get("")
def get_all_settings(db: Session = Depends(get_db)):
    """
    Get all application settings with their current values.

    Returns both the schema (type, label, options) and current values.
    Settings not yet saved in DB use their defaults.
    """
    result = {}
    for key, schema in SETTINGS_SCHEMA.items():
        db_value = get_setting(db, key)
        result[key] = {
            **schema,
            "value": db_value if db_value is not None else schema["default"],
        }
    return result


@router.get("/schema")
def get_settings_schema():
    """Get the settings schema (no current values)."""
    return SETTINGS_SCHEMA


@router.get("/{key}")
def get_single_setting(key: str, db: Session = Depends(get_db)):
    """Get a single setting by key."""
    if key not in SETTINGS_SCHEMA:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")

    schema = SETTINGS_SCHEMA[key]
    db_value = get_setting(db, key)

    return {
        **schema,
        "key": key,
        "value": db_value if db_value is not None else schema["default"],
    }


@router.put("/{key}")
def update_single_setting(key: str, body: SettingUpdate, db: Session = Depends(get_db)):
    """Update a single setting."""
    from fastapi import HTTPException

    if key not in SETTINGS_SCHEMA:
        raise HTTPException(status_code=404, detail=f"Unknown setting: {key}")

    schema = SETTINGS_SCHEMA[key]

    # Validate value
    if schema["type"] == "select" and "options" in schema:
        if body.value not in schema["options"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value. Options: {schema['options']}",
            )

    if schema["type"] == "number":
        try:
            num = int(body.value)
            if "min" in schema and num < schema["min"]:
                raise HTTPException(status_code=400, detail=f"Value must be >= {schema['min']}")
            if "max" in schema and num > schema["max"]:
                raise HTTPException(status_code=400, detail=f"Value must be <= {schema['max']}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Value must be a number")

    set_setting(db, key, body.value)
    logger.info("Setting updated: %s = %s", key, body.value)

    return {
        **schema,
        "key": key,
        "value": body.value,
    }


@router.put("")
def update_bulk_settings(body: SettingsBulkUpdate, db: Session = Depends(get_db)):
    """Update multiple settings at once."""
    from fastapi import HTTPException

    updated = {}
    for key, value in body.settings.items():
        if key not in SETTINGS_SCHEMA:
            continue

        schema = SETTINGS_SCHEMA[key]

        # Basic validation
        if schema["type"] == "select" and "options" in schema:
            if value not in schema["options"]:
                continue

        if schema["type"] == "number":
            try:
                num = int(value)
                if "min" in schema and num < schema["min"]:
                    continue
                if "max" in schema and num > schema["max"]:
                    continue
            except ValueError:
                continue

        set_setting(db, key, value)
        updated[key] = value

    logger.info("Bulk settings updated: %d settings", len(updated))
    return {"updated": updated, "count": len(updated)}


@router.get("/directories/info")
def get_directory_info():
    """Get info about configured directories (read-only, from .env)."""
    return {
        "video_input_dir": settings.VIDEO_INPUT_DIR,
        "subtitle_output_dir": settings.SUBTITLE_OUTPUT_DIR,
        "video_output_dir": settings.VIDEO_OUTPUT_DIR,
        "model_dir": settings.MODEL_DIR,
        "temp_dir": settings.TEMP_DIR,
        "db_path": settings.DB_PATH,
    }
