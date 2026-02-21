from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.config.settings import settings
from backend.db.database import SessionLocal
from backend.db.models import Batch, Job
from backend.tasks.callbacks import get_latest_progress

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str):
    """
    Endpoint WebSocket cho tiến trình công việc thời gian thực.

    Đăng ký kênh Redis pub/sub cho công việc và chuyển tiếp
    sự kiện tiến trình đến client. Gửi tiến trình mới nhất đã cache
    khi kết nối cho client tham gia muộn.
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
        logger.debug("WebSocket ngắt kết nối cho công việc %s", job_id)
    except Exception as e:
        logger.error("Lỗi WebSocket cho công việc %s: %s", job_id, e)
    finally:
        await pubsub.unsubscribe(f"job:{job_id}:progress")
        await pubsub.close()
        await r.close()


@router.websocket("/ws/model-download/{task_id}")
async def model_download_progress_ws(websocket: WebSocket, task_id: str):
    """
    WebSocket cho tiến trình tải mô hình Whisper.
    Đăng ký kênh Redis pub/sub và chuyển tiếp tiến trình đến client.
    """
    await websocket.accept()

    # Send latest cached progress if available
    try:
        r_sync = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        latest = await r_sync.get(f"model_download:{task_id}:latest")
        if latest:
            await websocket.send_text(latest)
        await r_sync.close()
    except Exception:
        pass

    # Subscribe to Redis pub/sub
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()

    try:
        await pubsub.subscribe(f"model_download:{task_id}")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message["type"] == "message":
                await websocket.send_text(message["data"])

                data = json.loads(message["data"])
                if data.get("status") in ("completed", "failed"):
                    break

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
        logger.debug("WebSocket ngắt kết nối cho tải mô hình %s", task_id)
    except Exception as e:
        logger.error("Lỗi WebSocket cho tải mô hình %s: %s", task_id, e)
    finally:
        await pubsub.unsubscribe(f"model_download:{task_id}")
        await pubsub.close()
        await r.close()


@router.websocket("/ws/batch/{batch_id}")
async def batch_progress_ws(websocket: WebSocket, batch_id: str):
    """
    Endpoint WebSocket cho tiến trình batch thời gian thực.

    Đăng ký tất cả kênh công việc trong batch và gửi
    cập nhật tiến trình tổng hợp đến client.
    """
    await websocket.accept()

    # Get batch jobs
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            await websocket.send_json({"error": "Không tìm thấy batch"})
            await websocket.close()
            return

        jobs = db.query(Job).filter(Job.batch_id == batch_id).all()
        job_ids = [j.id for j in jobs]
    finally:
        db.close()

    if not job_ids:
        await websocket.send_json({"error": "Batch không có công việc nào"})
        await websocket.close()
        return

    # Send initial aggregate progress
    await _send_batch_progress(websocket, batch_id, job_ids)

    # Subscribe to all job channels
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()

    try:
        channels = [f"job:{jid}:progress" for jid in job_ids]
        await pubsub.subscribe(*channels)

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message["type"] == "message":
                # Forward individual job update
                data = json.loads(message["data"])
                await websocket.send_json({
                    "type": "job_update",
                    **data,
                })

                # Send aggregate progress
                await _send_batch_progress(websocket, batch_id, job_ids)

            # Check client connection
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
        logger.debug("WebSocket ngắt kết nối cho batch %s", batch_id)
    except Exception as e:
        logger.error("Lỗi WebSocket cho batch %s: %s", batch_id, e)
    finally:
        for jid in job_ids:
            await pubsub.unsubscribe(f"job:{jid}:progress")
        await pubsub.close()
        await r.close()


async def _send_batch_progress(websocket: WebSocket, batch_id: str, job_ids: list[str]):
    """Tính toán và gửi tiến trình tổng hợp của batch."""
    job_progresses = []
    for jid in job_ids:
        latest = get_latest_progress(jid)
        if latest:
            job_progresses.append(latest)

    # Also check DB for completed jobs that no longer have Redis cache
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.batch_id == batch_id).all()
        total = len(jobs)
        completed = sum(1 for j in jobs if j.status == "COMPLETED")
        failed = sum(1 for j in jobs if j.status == "FAILED")
        processing = sum(1 for j in jobs if j.status == "PROCESSING")
        queued = sum(1 for j in jobs if j.status == "QUEUED")

        total_progress = sum(j.progress_percent or 0 for j in jobs)
        overall = total_progress / total if total > 0 else 0

        all_done = completed + failed >= total and queued == 0 and processing == 0
    finally:
        db.close()

    await websocket.send_json({
        "type": "batch_progress",
        "batch_id": batch_id,
        "overall_percent": round(overall, 1),
        "total": total,
        "completed": completed,
        "failed": failed,
        "processing": processing,
        "queued": queued,
        "all_done": all_done,
    })
