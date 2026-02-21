from fastapi import APIRouter

from backend.api import batch, files, jobs, languages, models_api, presets, settings_api, system, websocket

api_router = APIRouter(prefix="/api")

api_router.include_router(system.router)
api_router.include_router(jobs.router)
api_router.include_router(batch.router)
api_router.include_router(languages.router)
api_router.include_router(models_api.router)
api_router.include_router(presets.router)
api_router.include_router(files.router)
api_router.include_router(settings_api.router)
api_router.include_router(websocket.router)
