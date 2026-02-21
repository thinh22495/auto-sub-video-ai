"""Các endpoint API cài đặt ứng dụng."""

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


# Các khóa cài đặt và giá trị mặc định (lấy từ settings.py)
SETTINGS_SCHEMA: dict[str, dict] = {
    "default_whisper_model": {
        "type": "select",
        "label": "Mô hình Whisper mặc định",
        "description": "Mô hình chuyển giọng nói thành văn bản cho công việc mới",
        "default": settings.DEFAULT_WHISPER_MODEL,
        "options": ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"],
        "category": "models",
    },
    "default_ollama_model": {
        "type": "text",
        "label": "Mô hình Ollama mặc định",
        "description": "Mô hình dịch thuật mặc định (vd: qwen2.5:7b)",
        "default": settings.DEFAULT_OLLAMA_MODEL,
        "category": "models",
    },
    "default_subtitle_format": {
        "type": "select",
        "label": "Định dạng phụ đề mặc định",
        "description": "Định dạng đầu ra mặc định cho công việc mới",
        "default": settings.DEFAULT_SUBTITLE_FORMAT,
        "options": ["srt", "ass", "vtt"],
        "category": "subtitles",
    },
    "default_max_line_length": {
        "type": "number",
        "label": "Độ dài dòng tối đa",
        "description": "Số ký tự tối đa mỗi dòng phụ đề",
        "default": str(settings.DEFAULT_MAX_LINE_LENGTH),
        "min": 20,
        "max": 80,
        "category": "subtitles",
    },
    "default_max_lines": {
        "type": "number",
        "label": "Số dòng tối đa",
        "description": "Số dòng tối đa mỗi phụ đề",
        "default": str(settings.DEFAULT_MAX_LINES),
        "min": 1,
        "max": 4,
        "category": "subtitles",
    },
    "max_concurrent_jobs": {
        "type": "number",
        "label": "Số công việc đồng thời tối đa",
        "description": "Số công việc xử lý đồng thời tối đa",
        "default": str(settings.MAX_CONCURRENT_JOBS),
        "min": 1,
        "max": 10,
        "category": "processing",
    },
    "temp_file_max_age_hours": {
        "type": "number",
        "label": "Thời gian lưu file tạm tối đa (giờ)",
        "description": "Tự động xóa file tạm cũ hơn thời gian này",
        "default": str(settings.TEMP_FILE_MAX_AGE_HOURS),
        "min": 1,
        "max": 168,
        "category": "cleanup",
    },
    "completed_job_retention_days": {
        "type": "number",
        "label": "Thời gian lưu công việc (ngày)",
        "description": "Giữ hồ sơ công việc hoàn thành trong số ngày này",
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
    Lấy tất cả cài đặt ứng dụng cùng giá trị hiện tại.

    Trả về cả schema (kiểu, nhãn, tùy chọn) và giá trị hiện tại.
    Các cài đặt chưa lưu trong DB sẽ sử dụng giá trị mặc định.
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
    """Lấy schema cài đặt (không có giá trị hiện tại)."""
    return SETTINGS_SCHEMA


@router.get("/{key}")
def get_single_setting(key: str, db: Session = Depends(get_db)):
    """Lấy một cài đặt theo khóa."""
    if key not in SETTINGS_SCHEMA:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Cài đặt không xác định: {key}")

    schema = SETTINGS_SCHEMA[key]
    db_value = get_setting(db, key)

    return {
        **schema,
        "key": key,
        "value": db_value if db_value is not None else schema["default"],
    }


@router.put("/{key}")
def update_single_setting(key: str, body: SettingUpdate, db: Session = Depends(get_db)):
    """Cập nhật một cài đặt."""
    from fastapi import HTTPException

    if key not in SETTINGS_SCHEMA:
        raise HTTPException(status_code=404, detail=f"Cài đặt không xác định: {key}")

    schema = SETTINGS_SCHEMA[key]

    # Kiểm tra giá trị
    if schema["type"] == "select" and "options" in schema:
        if body.value not in schema["options"]:
            raise HTTPException(
                status_code=400,
                detail=f"Giá trị không hợp lệ. Các tùy chọn: {schema['options']}",
            )

    if schema["type"] == "number":
        try:
            num = int(body.value)
            if "min" in schema and num < schema["min"]:
                raise HTTPException(status_code=400, detail=f"Giá trị phải >= {schema['min']}")
            if "max" in schema and num > schema["max"]:
                raise HTTPException(status_code=400, detail=f"Giá trị phải <= {schema['max']}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Giá trị phải là số")

    set_setting(db, key, body.value)
    logger.info("Đã cập nhật cài đặt: %s = %s", key, body.value)

    return {
        **schema,
        "key": key,
        "value": body.value,
    }


@router.put("")
def update_bulk_settings(body: SettingsBulkUpdate, db: Session = Depends(get_db)):
    """Cập nhật nhiều cài đặt cùng lúc."""
    from fastapi import HTTPException

    updated = {}
    for key, value in body.settings.items():
        if key not in SETTINGS_SCHEMA:
            continue

        schema = SETTINGS_SCHEMA[key]

        # Kiểm tra cơ bản
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

    logger.info("Đã cập nhật hàng loạt: %d cài đặt", len(updated))
    return {"updated": updated, "count": len(updated)}


@router.get("/directories/info")
def get_directory_info():
    """Lấy thông tin về các thư mục đã cấu hình (chỉ đọc, từ .env)."""
    return {
        "video_input_dir": settings.VIDEO_INPUT_DIR,
        "subtitle_output_dir": settings.SUBTITLE_OUTPUT_DIR,
        "video_output_dir": settings.VIDEO_OUTPUT_DIR,
        "model_dir": settings.MODEL_DIR,
        "temp_dir": settings.TEMP_DIR,
        "db_path": settings.DB_PATH,
    }
