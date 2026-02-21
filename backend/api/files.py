"""Các endpoint API duyệt tệp, tải lên và tải xuống."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from backend.config.settings import settings
from backend.files.file_manager import (
    browse_directory,
    delete_file,
    get_disk_usage,
    get_root_directories,
    save_upload,
    save_upload_chunk,
)
from backend.files.video_info import get_video_info, is_video_file
from backend.utils.security import is_safe_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


# ---------- Schemas ----------

class ChunkUploadRequest(BaseModel):
    filename: str
    chunk_index: int
    total_chunks: int
    upload_id: str


# ---------- Endpoints ----------

@router.get("/roots")
def list_roots():
    """Liệt kê các thư mục gốc có thể duyệt."""
    return get_root_directories()


@router.get("/browse")
def browse(path: Optional[str] = Query(None, description="Directory path to browse")):
    """
    Duyệt thư mục và liệt kê nội dung.

    Trả về tệp và thư mục con với loại, kích thước và thời gian sửa đổi.
    Nếu không chỉ định đường dẫn, mặc định là thư mục video đầu vào.
    """
    try:
        return browse_directory(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư mục")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/info")
def file_info(path: str = Query(..., description="File path")):
    """Lấy thông tin chi tiết về tệp. Với video, trả về codec/độ phân giải/thời lượng."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")

    import os
    allowed = [
        os.path.realpath(settings.VIDEO_INPUT_DIR),
        os.path.realpath(settings.SUBTITLE_OUTPUT_DIR),
        os.path.realpath(settings.VIDEO_OUTPUT_DIR),
    ]
    if not is_safe_path(path, allowed):
        raise HTTPException(status_code=403, detail="Truy cập bị từ chối")

    stat = p.stat()
    result = {
        "name": p.name,
        "path": str(p),
        "size_bytes": stat.st_size,
        "modified": stat.st_mtime,
        "extension": p.suffix.lower(),
        "is_video": is_video_file(p.name),
    }

    if is_video_file(p.name):
        result["video_info"] = get_video_info(str(p))

    return result


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    target_dir: Optional[str] = Query(None, description="Target directory"),
):
    """
    Tải lên tệp (tải lên một lần).

    Với tệp lớn (>100MB), hãy sử dụng endpoint tải lên phân đoạn.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Không có tên tệp")

    # Check file size limit
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Tệp quá lớn. Tối đa: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    try:
        path = save_upload(file.filename, content, target_dir)
        return {
            "status": "uploaded",
            "path": path,
            "filename": Path(path).name,
            "size_bytes": len(content),
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/upload/chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    filename: str = Query(...),
    chunk_index: int = Query(..., ge=0),
    total_chunks: int = Query(..., ge=1),
    upload_id: str = Query(None),
):
    """
    Tải lên phân đoạn tệp cho hỗ trợ tệp lớn.

    Client chia tệp thành các phần và tải lên từng phần.
    Khi nhận phần cuối cùng, tệp được ghép lại.
    """
    if not upload_id:
        upload_id = str(uuid.uuid4())

    content = await file.read()

    try:
        result = save_upload_chunk(
            filename=filename,
            chunk=content,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            upload_id=upload_id,
        )
        result["upload_id"] = upload_id
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/download")
def download_file(path: str = Query(..., description="File path to download")):
    """Tải xuống tệp từ máy chủ."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    if not p.is_file():
        raise HTTPException(status_code=400, detail="Đường dẫn không phải tệp")

    import os
    allowed = [
        os.path.realpath(settings.VIDEO_INPUT_DIR),
        os.path.realpath(settings.SUBTITLE_OUTPUT_DIR),
        os.path.realpath(settings.VIDEO_OUTPUT_DIR),
    ]
    if not is_safe_path(path, allowed):
        raise HTTPException(status_code=403, detail="Truy cập bị từ chối")

    # Determine media type
    suffix = p.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".avi": "video/x-msvideo",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".srt": "text/plain",
        ".ass": "text/plain",
        ".vtt": "text/vtt",
    }

    return FileResponse(
        str(p),
        filename=p.name,
        media_type=media_types.get(suffix, "application/octet-stream"),
    )


@router.get("/video/stream")
def stream_video(path: str = Query(..., description="Video file path")):
    """Phát trực tuyến video cho xem trước trên trình duyệt (hỗ trợ range requests)."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy video")

    import os
    allowed = [
        os.path.realpath(settings.VIDEO_INPUT_DIR),
        os.path.realpath(settings.VIDEO_OUTPUT_DIR),
    ]
    if not is_safe_path(path, allowed):
        raise HTTPException(status_code=403, detail="Truy cập bị từ chối")

    suffix = p.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    }

    return FileResponse(
        str(p),
        media_type=media_types.get(suffix, "video/mp4"),
    )


@router.delete("/delete")
def remove_file(path: str = Query(..., description="File path to delete")):
    """Xóa tệp từ máy chủ."""
    try:
        if delete_file(path):
            return {"status": "deleted", "path": path}
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/disk")
def disk_usage():
    """Lấy thông tin sử dụng đĩa cho tất cả thư mục dữ liệu."""
    return {
        "videos": get_disk_usage(settings.VIDEO_INPUT_DIR),
        "subtitles": get_disk_usage(settings.SUBTITLE_OUTPUT_DIR),
        "output": get_disk_usage(settings.VIDEO_OUTPUT_DIR),
        "models": get_disk_usage(settings.MODEL_DIR),
    }
