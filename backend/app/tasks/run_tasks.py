"""Celery tasks. Thin wrappers over the same pipeline the CLI uses; the plain
`do_*` functions hold the logic so behaviour is identical to a manual run."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from app.db import session_scope
from app.logging_config import log_event
from app.models import Brand
from app.pipeline.runner import run_brand_prompts, run_single_prompt
from app.pipeline.scoring import recompute_scores
from app.tasks.celery_app import celery_app

log = logging.getLogger("limelight.tasks")


def active_brand_ids(db) -> list[str]:
    return [str(b) for b in db.scalars(select(Brand.id).order_by(Brand.created_at))]


def do_run_brand(brand_id: str) -> int:
    """Run all active prompts for a brand, then recompute its scores."""
    bid = uuid.UUID(brand_id)
    with session_scope() as db:
        runs = run_brand_prompts(db, bid)
        recompute_scores(db, bid)
    log_event(log, "task.run_brand.done", brand_id=brand_id, runs=len(runs))
    return len(runs)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.run_tasks.run_prompt")
def run_prompt(self, prompt_id: str) -> str:
    try:
        with session_scope() as db:
            run = run_single_prompt(db, uuid.UUID(prompt_id))
            return str(run.id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 15)


@celery_app.task(bind=True, max_retries=3, name="app.tasks.run_tasks.run_brand")
def run_brand(self, brand_id: str) -> int:
    try:
        return do_run_brand(brand_id)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


@celery_app.task(name="app.tasks.run_tasks.run_all_brands")
def run_all_brands() -> int:
    """Beat entrypoint: enqueue a run for every brand (fan-out per brand)."""
    with session_scope() as db:
        ids = active_brand_ids(db)
    for bid in ids:
        run_brand.delay(bid)
    log_event(log, "task.run_all_brands.enqueued", brands=len(ids))
    return len(ids)
