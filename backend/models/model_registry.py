from __future__ import annotations

import logging

from backend.models import ollama_manager, whisper_manager

logger = logging.getLogger(__name__)


def get_all_models() -> dict:
    """Get summary of all models across all engines."""
    return {
        "whisper": whisper_manager.list_models(),
        "ollama": ollama_manager.list_models(),
    }


def get_system_model_status() -> dict:
    """Quick status check for all model systems."""
    whisper_models = whisper_manager.list_models()
    whisper_downloaded = [m for m in whisper_models if m["downloaded"]]

    ollama_health = ollama_manager.check_health()
    ollama_models = ollama_manager.list_models()

    return {
        "whisper": {
            "available_count": len(whisper_models),
            "downloaded_count": len(whisper_downloaded),
            "downloaded": [m["name"] for m in whisper_downloaded],
        },
        "ollama": {
            "status": ollama_health["status"],
            "model_count": len(ollama_models),
            "models": [m["name"] for m in ollama_models],
        },
    }
