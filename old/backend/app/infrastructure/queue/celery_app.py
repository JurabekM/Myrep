"""Celery application (RabbitMQ broker, Redis result backend)."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_advisor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.infrastructure.queue.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
    task_default_retry_delay=30,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    # lex.uz korpusini har kuni yangilash (o'zgargan hujjatlar qayta indekslanadi)
    "refresh-lex-corpus": {
        "task": "app.infrastructure.queue.tasks.refresh_lex_corpus",
        "schedule": 24 * 3600,
    },
}
