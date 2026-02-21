import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    logger.info("AutoSubAI đang khởi động...")
    # Startup: create tables and ensure directories exist
    settings.ensure_directories()
    Base.metadata.create_all(bind=engine)
    logger.info("Đã khởi tạo cơ sở dữ liệu, đã tạo thư mục.")
    yield
    logger.info("AutoSubAI đang tắt.")


app = FastAPI(
    title="AutoSubAI",
    description="Công cụ tạo phụ đề video ngoại tuyến",
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
