"""Orchestration: run (prompt × engine), persist an immutable run plus its
mentions and citations. The CLI and the Celery tasks both call in here — one
code path.

This module is engine-agnostic: it resolves a provider by key and consumes the
normalized EngineResult. It never imports a specific provider.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brand, Citation, Competitor, Engine, Mention, Prompt, Run
from app.pipeline.citations import dedupe_citations
from app.pipeline.detection import Entity, detect_mentions
from app.providers.registry import get_provider

DEFAULT_ENGINE_KEY = "openai"  # Phase 1 is single-engine.


def _entities_for_brand(db: Session, brand: Brand) -> list[Entity]:
    entities = [Entity(name=brand.display_name, aliases=list(brand.aliases or []), is_tracked_brand=True)]
    competitors = db.scalars(select(Competitor).where(Competitor.brand_id == brand.id))
    for c in competitors:
        entities.append(Entity(name=c.name, aliases=list(c.aliases or []), is_tracked_brand=False))
    return entities


def _engine_row(db: Session, key: str) -> Engine:
    engine = db.scalar(select(Engine).where(Engine.key == key))
    if engine is None:
        raise ValueError(f"engine {key!r} not seeded — run `cli seed`")
    return engine


def run_single_prompt(
    db: Session, prompt_id: uuid.UUID, engine_key: str = DEFAULT_ENGINE_KEY
) -> Run:
    """Execute one prompt through one engine and persist the run + mentions + citations."""
    prompt = db.get(Prompt, prompt_id)
    if prompt is None:
        raise ValueError(f"prompt {prompt_id} not found")
    brand = db.get(Brand, prompt.brand_id)
    engine = _engine_row(db, engine_key)

    provider = get_provider(engine_key)
    result = provider.run(prompt.text)

    run = Run(
        prompt_id=prompt.id,
        engine_id=engine.id,
        answer_text=result.answer_text,
        raw_response_json=result.raw,
    )
    db.add(run)
    db.flush()  # assign run.id

    for m in detect_mentions(result.answer_text, _entities_for_brand(db, brand)):
        db.add(
            Mention(
                run_id=run.id,
                entity_type=m.entity_type,
                entity_name=m.entity_name,
                is_tracked_brand=m.is_tracked_brand,
                position=m.position,
                prominence=m.prominence,
            )
        )

    for c in dedupe_citations(result.cited_urls):
        db.add(Citation(run_id=run.id, url=c.url, domain=c.domain))

    db.flush()
    return run


def run_brand_prompts(
    db: Session, brand_id: uuid.UUID, engine_key: str = DEFAULT_ENGINE_KEY
) -> list[Run]:
    """Run every active prompt for a brand. Errors on one prompt don't sink the rest."""
    prompt_ids = list(
        db.scalars(
            select(Prompt.id).where(Prompt.brand_id == brand_id, Prompt.active.is_(True))
        )
    )
    runs: list[Run] = []
    for pid in prompt_ids:
        runs.append(run_single_prompt(db, pid, engine_key))
    return runs
