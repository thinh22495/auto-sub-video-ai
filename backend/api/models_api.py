from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.config.settings import settings
from backend.models import ollama_manager, whisper_manager, model_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


# ---------- Schemas ----------

class ModelDownloadRequest(BaseModel):
    name: str


# ---------- Whisper endpoints ----------

@router.get("/whisper")
def list_whisper_models():
    """List all available Whisper models with download status."""
    return whisper_manager.list_models()


@router.post("/whisper/download", status_code=202)
def download_whisper_model(req: ModelDownloadRequest):
    """Dispatch Whisper model download as background task."""
    if req.name not in whisper_manager.WHISPER_MODELS:
        raise HTTPException(status_code=400, detail=f"Mô hình không xác định: {req.name}")

    from backend.tasks.tasks import download_whisper_model as download_task
    task = download_task.apply_async(args=[req.name])

    return {
        "task_id": task.id,
        "model_name": req.name,
        "status": "queued",
    }


@router.get("/whisper/download/{task_id}/status")
def get_download_status(task_id: str):
    """Check status of a model download task."""
    import redis as sync_redis
    from backend.config.settings import settings as app_settings

    r = sync_redis.from_url(app_settings.REDIS_URL, decode_responses=True)
    latest = r.get(f"model_download:{task_id}:latest")
    r.close()

    if latest:
        import json
        return json.loads(latest)

    return {"task_id": task_id, "status": "pending", "progress_percent": 0, "message": "Đang chờ..."}


@router.delete("/whisper/{model_name}")
def delete_whisper_model(model_name: str):
    """Delete a cached Whisper model."""
    try:
        deleted = whisper_manager.delete_model(model_name)
        if deleted:
            return {"message": f"Model {model_name} deleted", "name": model_name}
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found on disk")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Ollama endpoints ----------

@router.get("/ollama")
def list_ollama_models():
    """List all models available in the Ollama instance."""
    return ollama_manager.list_models()


@router.get("/ollama/recommended")
def list_recommended_models():
    """List recommended Ollama models for translation."""
    installed = ollama_manager.list_models()
    installed_names = {m["name"] for m in installed}

    result = []
    for rec in ollama_manager.RECOMMENDED_MODELS:
        result.append({
            **rec,
            "installed": rec["name"] in installed_names,
        })
    return result


@router.post("/ollama/pull")
def pull_ollama_model(req: ModelDownloadRequest):
    """Pull (download) an Ollama model. Streams progress."""
    import json

    def generate():
        try:
            for progress in ollama_manager.pull_model(req.name):
                yield json.dumps(progress) + "\n"
        except Exception as e:
            yield json.dumps({"status": "error", "error": str(e)}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


@router.delete("/ollama/{model_name:path}")
def delete_ollama_model(model_name: str):
    """Delete an Ollama model."""
    deleted = ollama_manager.delete_model(model_name)
    if deleted:
        return {"message": f"Model {model_name} deleted", "name": model_name}
    raise HTTPException(status_code=500, detail=f"Failed to delete model {model_name}")


@router.get("/ollama/{model_name:path}/info")
def get_ollama_model_info(model_name: str):
    """Get detailed info about a specific Ollama model."""
    info = ollama_manager.get_model_info(model_name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    return info


@router.get("/ollama/health")
def ollama_health():
    """Check Ollama service health."""
    return ollama_manager.check_health()


# ---------- Debug ----------

@router.get("/whisper/debug")
def debug_whisper_cache():
    """Debug endpoint: kiểm tra chi tiết trạng thái cache Whisper."""
    import os
    from pathlib import Path

    results = {}
    for name in whisper_manager.WHISPER_MODELS:
        is_cached, path, size_mb = whisper_manager._check_model_cached(name)
        results[name] = {
            "is_cached": is_cached,
            "path": str(path) if path else None,
            "size_mb": round(size_mb, 1),
        }

    env_info = {
        "HF_HOME": os.environ.get("HF_HOME"),
        "HF_HUB_CACHE": None,
        "MODEL_DIR": settings.MODEL_DIR,
        "hf_cache_dirs": [str(d) for d in whisper_manager._get_hf_cache_dirs()],
    }

    try:
        from huggingface_hub import constants as hf_constants
        env_info["HF_HUB_CACHE"] = hf_constants.HF_HUB_CACHE
    except Exception:
        pass

    return {"models": results, "env": env_info}


# ---------- Registry ----------

@router.get("/status")
def models_status():
    """Get summary status of all model systems."""
    return model_registry.get_system_model_status()
