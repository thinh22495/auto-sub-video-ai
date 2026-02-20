from __future__ import annotations

import logging
from typing import Generator

import httpx

from backend.config.settings import settings

logger = logging.getLogger(__name__)


def list_models() -> list[dict]:
    """List all models available in the Ollama instance."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()

        models = []
        for m in data.get("models", []):
            models.append({
                "name": m.get("name", ""),
                "size_bytes": m.get("size", 0),
                "size_gb": round(m.get("size", 0) / (1024**3), 2),
                "modified_at": m.get("modified_at", ""),
                "digest": m.get("digest", "")[:12],
                "family": m.get("details", {}).get("family", ""),
                "parameter_size": m.get("details", {}).get("parameter_size", ""),
                "quantization": m.get("details", {}).get("quantization_level", ""),
                "is_default": m.get("name", "") == settings.DEFAULT_OLLAMA_MODEL,
            })
        return models

    except httpx.ConnectError:
        logger.warning("Cannot connect to Ollama at %s", settings.OLLAMA_BASE_URL)
        return []
    except Exception as e:
        logger.error("Failed to list Ollama models: %s", e)
        return []


def pull_model(model_name: str) -> Generator[dict, None, None]:
    """
    Pull (download) a model from Ollama registry.
    Yields progress updates as dicts.
    """
    logger.info("Pulling Ollama model: %s", model_name)

    with httpx.Client(timeout=None) as client:
        with client.stream(
            "POST",
            f"{settings.OLLAMA_BASE_URL}/api/pull",
            json={"name": model_name, "stream": True},
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    import json
                    data = json.loads(line)
                    status = data.get("status", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)

                    progress = {
                        "status": status,
                        "total": total,
                        "completed": completed,
                        "percent": round((completed / total) * 100, 1) if total > 0 else 0,
                    }
                    yield progress

                    if status == "success":
                        logger.info("Ollama model pulled: %s", model_name)
                        return

                except Exception:
                    continue


def pull_model_sync(model_name: str) -> dict:
    """Pull a model synchronously (blocking). Returns final status."""
    last_progress = {"status": "unknown", "percent": 0}
    try:
        for progress in pull_model(model_name):
            last_progress = progress
        return {"name": model_name, "status": "success", **last_progress}
    except Exception as e:
        logger.error("Failed to pull Ollama model %s: %s", model_name, e)
        return {"name": model_name, "status": "error", "error": str(e)}


def delete_model(model_name: str) -> bool:
    """Delete a model from Ollama."""
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.delete(
                f"{settings.OLLAMA_BASE_URL}/api/delete",
                json={"name": model_name},
            )
            if resp.status_code == 200:
                logger.info("Deleted Ollama model: %s", model_name)
                return True
            else:
                logger.warning(
                    "Failed to delete Ollama model %s: %d %s",
                    model_name, resp.status_code, resp.text,
                )
                return False
    except Exception as e:
        logger.error("Failed to delete Ollama model %s: %s", model_name, e)
        return False


def get_model_info(model_name: str) -> dict | None:
    """Get detailed info about a specific Ollama model."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{settings.OLLAMA_BASE_URL}/api/show",
                json={"name": model_name},
            )
            if resp.status_code != 200:
                return None
            return resp.json()
    except Exception:
        return None


def check_health() -> dict:
    """Check if Ollama service is healthy."""
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            model_count = len(resp.json().get("models", []))
            return {
                "status": "up",
                "url": settings.OLLAMA_BASE_URL,
                "model_count": model_count,
            }
    except httpx.ConnectError:
        return {"status": "down", "url": settings.OLLAMA_BASE_URL, "error": "Connection refused"}
    except Exception as e:
        return {"status": "error", "url": settings.OLLAMA_BASE_URL, "error": str(e)}


# Recommended models for translation
RECOMMENDED_MODELS = [
    {
        "name": "qwen2.5:7b",
        "description": "Best multilingual model. 29+ languages including Vietnamese, Japanese, Korean, Chinese.",
        "size_gb": 4.7,
        "languages": "multilingual (29+)",
    },
    {
        "name": "qwen2.5:3b",
        "description": "Lighter multilingual model. Good for systems with limited VRAM.",
        "size_gb": 2.0,
        "languages": "multilingual (29+)",
    },
    {
        "name": "llama3.1:8b",
        "description": "Strong English-centric model. Good for EN translation tasks.",
        "size_gb": 4.7,
        "languages": "English-focused, basic multilingual",
    },
    {
        "name": "mistral:7b",
        "description": "Good for European languages. French, German, Spanish, Italian, etc.",
        "size_gb": 4.1,
        "languages": "European languages",
    },
    {
        "name": "gemma2:9b",
        "description": "Google's model. Good general multilingual performance.",
        "size_gb": 5.4,
        "languages": "multilingual",
    },
]
