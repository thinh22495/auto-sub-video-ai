"""Các endpoint API CRUD mẫu cài đặt."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Preset, generate_uuid
from backend.video.presets import list_builtin_presets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/presets", tags=["presets"])


# ---------- Pydantic Schemas ----------

class SubtitleStyleInput(BaseModel):
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


class PresetCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    subtitle_style: SubtitleStyleInput
    video_settings: Optional[dict] = None


class PresetUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subtitle_style: Optional[SubtitleStyleInput] = None
    video_settings: Optional[dict] = None


# ---------- Helpers ----------

def _preset_to_dict(preset: Preset) -> dict:
    """Chuyển đổi model ORM Preset thành dict phản hồi."""
    style = preset.subtitle_style
    if isinstance(style, str):
        try:
            style = json.loads(style)
        except (json.JSONDecodeError, TypeError):
            style = {}

    video_settings = preset.video_settings
    if isinstance(video_settings, str):
        try:
            video_settings = json.loads(video_settings)
        except (json.JSONDecodeError, TypeError):
            video_settings = None

    return {
        "id": preset.id,
        "name": preset.name,
        "description": preset.description,
        "subtitle_style": style,
        "video_settings": video_settings,
        "is_builtin": preset.is_builtin,
        "created_at": preset.created_at.isoformat() if preset.created_at else None,
        "updated_at": preset.updated_at.isoformat() if preset.updated_at else None,
    }


# ---------- Endpoints ----------

@router.get("")
def list_presets(db: Session = Depends(get_db)):
    """Liệt kê tất cả mẫu (có sẵn + người dùng tạo)."""
    builtins = list_builtin_presets()

    user_presets = db.query(Preset).order_by(Preset.name).all()
    user_list = [_preset_to_dict(p) for p in user_presets]

    return builtins + user_list


@router.get("/builtin")
def get_builtin_presets():
    """Liệt kê chỉ các mẫu có sẵn."""
    return list_builtin_presets()


@router.get("/{preset_id}")
def get_preset(preset_id: str, db: Session = Depends(get_db)):
    """Lấy mẫu cụ thể theo ID."""
    # Check built-in presets first
    if preset_id.startswith("builtin_"):
        for bp in list_builtin_presets():
            if bp["id"] == preset_id:
                return bp
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu có sẵn")

    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu")

    return _preset_to_dict(preset)


@router.post("", status_code=201)
def create_preset(req: PresetCreateRequest, db: Session = Depends(get_db)):
    """Tạo mẫu người dùng mới."""
    # Check for duplicate name
    existing = db.query(Preset).filter(Preset.name == req.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Mẫu có tên '{req.name}' đã tồn tại")

    preset = Preset(
        id=generate_uuid(),
        name=req.name,
        description=req.description,
        subtitle_style=json.dumps(req.subtitle_style.model_dump()),
        video_settings=json.dumps(req.video_settings) if req.video_settings else None,
        is_builtin=False,
    )

    db.add(preset)
    db.commit()
    db.refresh(preset)

    logger.info("Created preset: %s (%s)", preset.name, preset.id)
    return _preset_to_dict(preset)


@router.put("/{preset_id}")
def update_preset(preset_id: str, req: PresetUpdateRequest, db: Session = Depends(get_db)):
    """Cập nhật mẫu người dùng hiện có."""
    if preset_id.startswith("builtin_"):
        raise HTTPException(status_code=403, detail="Không thể sửa mẫu có sẵn")

    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu")

    if preset.is_builtin:
        raise HTTPException(status_code=403, detail="Không thể sửa mẫu có sẵn")

    if req.name is not None:
        # Check for duplicate name (excluding current preset)
        existing = db.query(Preset).filter(Preset.name == req.name, Preset.id != preset_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Mẫu có tên '{req.name}' đã tồn tại")
        preset.name = req.name

    if req.description is not None:
        preset.description = req.description

    if req.subtitle_style is not None:
        preset.subtitle_style = json.dumps(req.subtitle_style.model_dump())

    if req.video_settings is not None:
        preset.video_settings = json.dumps(req.video_settings)

    preset.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(preset)

    logger.info("Updated preset: %s (%s)", preset.name, preset.id)
    return _preset_to_dict(preset)


@router.delete("/{preset_id}")
def delete_preset(preset_id: str, db: Session = Depends(get_db)):
    """Xóa mẫu người dùng."""
    if preset_id.startswith("builtin_"):
        raise HTTPException(status_code=403, detail="Không thể xóa mẫu có sẵn")

    preset = db.query(Preset).filter(Preset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu")

    if preset.is_builtin:
        raise HTTPException(status_code=403, detail="Không thể xóa mẫu có sẵn")

    db.delete(preset)
    db.commit()

    logger.info("Deleted preset: %s (%s)", preset.name, preset_id)
    return {"message": "Đã xóa mẫu", "id": preset_id}


@router.post("/{preset_id}/duplicate", status_code=201)
def duplicate_preset(preset_id: str, db: Session = Depends(get_db)):
    """Nhân bản mẫu (có sẵn hoặc người dùng) thành mẫu người dùng mới."""
    source = None

    # Check built-in presets
    if preset_id.startswith("builtin_"):
        for bp in list_builtin_presets():
            if bp["id"] == preset_id:
                source = bp
                break
        if not source:
            raise HTTPException(status_code=404, detail="Không tìm thấy mẫu có sẵn")
    else:
        preset = db.query(Preset).filter(Preset.id == preset_id).first()
        if not preset:
            raise HTTPException(status_code=404, detail="Không tìm thấy mẫu")
        source = _preset_to_dict(preset)

    # Generate a unique name
    base_name = f"{source['name']} (Bản sao)"
    name = base_name
    counter = 1
    while db.query(Preset).filter(Preset.name == name).first():
        counter += 1
        name = f"{source['name']} (Bản sao {counter})"

    new_preset = Preset(
        id=generate_uuid(),
        name=name,
        description=source.get("description"),
        subtitle_style=json.dumps(source["subtitle_style"]),
        video_settings=json.dumps(source.get("video_settings")) if source.get("video_settings") else None,
        is_builtin=False,
    )

    db.add(new_preset)
    db.commit()
    db.refresh(new_preset)

    logger.info("Duplicated preset '%s' as '%s' (%s)", source["name"], name, new_preset.id)
    return _preset_to_dict(new_preset)
