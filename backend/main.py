import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.router import api_router
from backend.config.settings import settings
from backend.db.database import Base, engine
from backend.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

# Track server start time for uptime calculation
_start_time: float = 0.0


def get_uptime_seconds() -> float:
    return time.time() - _start_time


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time
    setup_logging()
    _start_time = time.time()
    logger.info("AutoSubAI starting up...")
    # Startup: create tables and ensure directories exist
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized, directories ensured.")
    yield
    logger.info("AutoSubAI shutting down.")


app = FastAPI(
    title="AutoSubAI",
    description="Offline video subtitle generation tool",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve frontend static files (built Next.js SPA)
frontend_dir = Path(__file__).parent.parent / "frontend" / "out"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
