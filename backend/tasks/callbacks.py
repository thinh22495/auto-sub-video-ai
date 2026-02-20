from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import redis

from backend.config.settings import settings
from backend.core.segment import ProgressInfo

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def publish_job_progress(job_id: str, progress: ProgressInfo, status: str = "PROCESSING"):
    """Publish job progress to Redis pub/sub for WebSocket consumers."""
    try:
        r = _get_redis()
        message = {
            "job_id": job_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **progress.to_dict(),
        }
        r.publish(f"job:{job_id}:progress", json.dumps(message))

        # Also store latest progress for clients that connect late
        r.set(
            f"job:{job_id}:latest_progress",
            json.dumps(message),
            ex=3600,  # expires in 1 hour
        )
    except Exception as e:
        logger.warning("Failed to publish progress for job %s: %s", job_id, e)


def get_latest_progress(job_id: str) -> dict | None:
    """Get the latest progress for a job (for late-joining clients)."""
    try:
        r = _get_redis()
        data = r.get(f"job:{job_id}:latest_progress")
        return json.loads(data) if data else None
    except Exception:
        return None


def clear_job_progress(job_id: str):
    """Clean up progress data after job completion."""
    try:
        r = _get_redis()
        r.delete(f"job:{job_id}:latest_progress")
    except Exception:
        pass


def create_progress_callback(job_id: str):
    """Create a progress callback function bound to a specific job ID."""

    def callback(progress: ProgressInfo):
        publish_job_progress(job_id, progress)

    return callback
