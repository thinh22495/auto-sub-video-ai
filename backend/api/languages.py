from fastapi import APIRouter

from backend.core.language_detector import get_supported_languages

router = APIRouter(tags=["languages"])


@router.get("/languages")
def list_languages():
    """List all supported languages for transcription/translation."""
    return get_supported_languages()
