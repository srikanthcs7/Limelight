"""Celery tasks. Thin wrappers over the same pipeline the CLI uses; the plain
`do_*` functions hold the logic so behaviour is identical to a manual run."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import session_scope
from app.logging_config import log_event
from app.models import Brand
from app.pipeline.runner import run_brand_all_engines, run_single_prompt
from app.pipeline.scoring import recompute_all_engines
from app.tasks.celery_app import celery_app

log = logging.getLogger("limelight.tasks")

# run_frequency -> minimum hours between scheduled runs.
FREQUENCY_HOURS = {"hourly": 1, "daily": 24, "weekly": 168}


def active_brand_ids(db) -> list[str]:
    return [str(b) for b in db.scalars(select(Brand.id).order_by(Brand.created_at))]


def is_due(brand: Brand, now: datetime) -> bool:
    """Whether the scheduler should run this brand now, per its frequency."""
    if brand.run_frequency == "manual":
        return False
    hours = FREQUENCY_HOURS.get(brand.run_frequency, 24)
    if brand.last_run_at is None:
        return True
    return (now - brand.last_run_at) >= timedelta(hours=hours)


def due_brand_ids(db, now: datetime) -> list[str]:
    """Return ids of brands due to run, stamping last_run_at so the next tick
    won't re-enqueue them within their window."""
    due = [b for b in db.scalars(select(Brand)) if is_due(b, now)]
    for b in due:
        b.last_run_at = now
    return [str(b.id) for b in due]


def do_run_brand(brand_id: str) -> dict:
    """Run all active prompts through every tracked engine, then recompute scores."""
    bid = uuid.UUID(brand_id)
    with session_scope() as db:
        per_engine = run_brand_all_engines(db, bid)
        recompute_all_engines(db, bid)
    log_event(log, "task.run_brand.done", brand_id=brand_id, by_engine=per_engine)
    return per_engine


@celery_app.task(bind=True, max_retries=3, name="app.tasks.run_tasks.run_prompt")
def run_prompt(self, prompt_id: str) -> str:
    try:
        with session_scope() as db:
            run = run_single_prompt(db, uuid.UUID(prompt_id))
            return str(run.id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 15)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.run_tasks.run_brand")
def run_brand(self, brand_id: str) -> dict:
    try:
        return do_run_brand(brand_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


@celery_app.task(name="app.tasks.run_tasks.dispatch_due_brands")
def dispatch_due_brands() -> int:
    """Beat entrypoint (hourly): enqueue a run for each brand whose configured
    frequency says it's due."""
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        ids = due_brand_ids(db, now)
    for bid in ids:
        run_brand.delay(bid)
    log_event(log, "task.dispatch.enqueued", brands=len(ids))
    return len(ids)


@celery_app.task(name="app.tasks.run_tasks.run_all_brands")
def run_all_brands() -> int:
    """Force a run of every brand regardless of frequency (manual/on-demand)."""
    with session_scope() as db:
        ids = active_brand_ids(db)
    for bid in ids:
        run_brand.delay(bid)
    log_event(log, "task.run_all_brands.enqueued", brands=len(ids))
    return len(ids)
