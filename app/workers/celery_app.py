from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "snowflake_loader",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_always_eager,
)

# Ensure task modules are registered when the worker starts.
import app.workers.tasks  # noqa: E402, F401
