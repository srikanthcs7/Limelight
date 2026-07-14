"""Celery app + beat schedule.

Broker/backend = REDIS_URL (Upstash `rediss://` in deployment, local redis in
Compose). Beat fires a daily fan-out that enqueues a run per active brand.
"""
from __future__ import annotations

import ssl

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings
from app.logging_config import configure_logging

configure_logging()
settings = get_settings()

celery_app = Celery("limelight", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    worker_max_tasks_per_child=200,
)

# Upstash (and any TLS Redis) uses rediss://; Celery needs an explicit ssl config.
if settings.redis_url.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_app.conf.redis_backend_use_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

# Hourly tick: the dispatcher enqueues only brands whose per-brand frequency
# (manual|hourly|daily|weekly) says they're due.
celery_app.conf.beat_schedule = {
    "dispatch-due-brands": {
        "task": "app.tasks.run_tasks.dispatch_due_brands",
        "schedule": crontab(minute=0),  # every hour on the hour
    },
}

# Register the task module.
from app.tasks import run_tasks  # noqa: E402,F401
