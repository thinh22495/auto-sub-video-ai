from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.config.settings import settings
from backend.tasks.callbacks import get_latest_progress

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress.

    Subscribes to Redis pub/sub channel for the job and forwards
    progress events to the client. Sends the latest cached progress
    on connect for late-joining clients.
    """
    await websocket.accept()

    # Send latest cached progress if available
    latest = get_latest_progress(job_id)
    if latest:
        await websocket.send_json(latest)

    # Subscribe to Redis pub/sub
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()

    try:
        await pubsub.subscribe(f"job:{job_id}:progress")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)

                # Close if job is done
                if data.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                    break

            # Check if client is still connected by sending a ping
            try:
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.01,
                )
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for job %s", job_id)
    except Exception as e:
        logger.error("WebSocket error for job %s: %s", job_id, e)
    finally:
        await pubsub.unsubscribe(f"job:{job_id}:progress")
        await pubsub.close()
        await r.close()
