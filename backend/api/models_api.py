from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


@router.post("/whisper/download")
def download_whisper_model(req: ModelDownloadRequest):
    """Download a Whisper model (triggers CTranslate2 download)."""
    try:
        result = whisper_manager.download_model(req.name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            "installed": any(rec["name"] in n for n in installed_names),
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


# ---------- Registry ----------

@router.get("/status")
def models_status():
    """Get summary status of all model systems."""
    return model_registry.get_system_model_status()
