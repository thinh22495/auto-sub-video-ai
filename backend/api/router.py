from fastapi import APIRouter

from backend.api import jobs, languages, models_api, system, websocket

api_router = APIRouter(prefix="/api")

api_router.include_router(system.router)
api_router.include_router(jobs.router)
api_router.include_router(languages.router)
api_router.include_router(models_api.router)
api_router.include_router(websocket.router)
