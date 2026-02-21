from celery import Celery

from backend.config.settings import settings

celery_app = Celery(
    "autosub",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 hours
    task_routes={
        "backend.tasks.tasks.extract_audio": {"queue": "ffmpeg_queue"},
        "backend.tasks.tasks.transcribe": {"queue": "gpu_queue"},
        "backend.tasks.tasks.diarize": {"queue": "gpu_queue"},
        "backend.tasks.tasks.translate": {"queue": "cpu_queue"},
        "backend.tasks.tasks.generate_subtitles": {"queue": "cpu_queue"},
        "backend.tasks.tasks.burn_in_subtitles": {"queue": "ffmpeg_queue"},
        "backend.tasks.tasks.download_whisper_model": {"queue": "gpu_queue"},
    },
)

celery_app.autodiscover_tasks(["backend.tasks"])
