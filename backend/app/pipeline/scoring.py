"""Visibility scoring. M1 computes a single all-time window; M3 adds rolling
7/30-day windows and prominence weighting from the LLM detection pass.

`composite_score` is a pure function (unit-tested) so the formula is verifiable
in isolation from the DB.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brand, Citation, Engine, Mention, Prompt, Run

# Composite weights — one place to tune. (spec §7 scoring)
W_MENTION = 0.40
W_SOV = 0.30
W_CITATION = 0.30


@dataclass
class ScoreComponents:
    total_runs: int
    mention_rate: float
    share_of_voice: float
    citation_rate: float
    prominence_weight: float
    visibility_score: float


def composite_score(
    mention_rate: float,
    share_of_voice: float,
    citation_rate: float,
    prominence_weight: float,
) -> float:
    """0–100 composite. mention_rate is weighted by how prominently the brand
    appears when it does show up."""
    raw = (
        W_MENTION * mention_rate * prominence_weight
        + W_SOV * share_of_voice
        + W_CITATION * citation_rate
    )
    return round(100.0 * raw, 2)


def compute_components(db: Session, brand: Brand, run_ids: list[uuid.UUID]) -> ScoreComponents:
    total = len(run_ids)
    if total == 0:
        return ScoreComponents(0, 0.0, 0.0, 0.0, 0.0, 0.0)

    brand_domain = (brand.domain or "").lower()
    runs_with_brand = 0
    runs_with_brand_citation = 0
    brand_mentions = 0
    competitor_mentions = 0
    prominence_sum = 0.0

    for rid in run_ids:
        mentions = list(db.scalars(select(Mention).where(Mention.run_id == rid)))
        brand_here = [m for m in mentions if m.is_tracked_brand]
        comp_here = [m for m in mentions if not m.is_tracked_brand]
        if brand_here:
            runs_with_brand += 1
            brand_mentions += len(brand_here)
            prominence_sum += max((m.prominence or 0.0) for m in brand_here)
        competitor_mentions += len(comp_here)

        cited_domains = {
            (d or "").lower() for d in db.scalars(select(Citation.domain).where(Citation.run_id == rid))
        }
        if brand_domain and brand_domain in cited_domains:
            runs_with_brand_citation += 1

    mention_rate = runs_with_brand / total
    denom = brand_mentions + competitor_mentions
    share_of_voice = (brand_mentions / denom) if denom else 0.0
    citation_rate = runs_with_brand_citation / total
    prominence_weight = (prominence_sum / runs_with_brand) if runs_with_brand else 0.0

    return ScoreComponents(
        total_runs=total,
        mention_rate=round(mention_rate, 4),
        share_of_voice=round(share_of_voice, 4),
        citation_rate=round(citation_rate, 4),
        prominence_weight=round(prominence_weight, 4),
        visibility_score=composite_score(
            mention_rate, share_of_voice, citation_rate, prominence_weight
        ),
    )


def _run_ids_in_window(
    db: Session,
    brand_id: uuid.UUID,
    engine_id: int,
    window_start: datetime | None,
    window_end: datetime,
) -> list[uuid.UUID]:
    prompt_ids = list(db.scalars(select(Prompt.id).where(Prompt.brand_id == brand_id)))
    if not prompt_ids:
        return []
    stmt = select(Run.id).where(Run.prompt_id.in_(prompt_ids), Run.engine_id == engine_id)
    if window_start is not None:
        stmt = stmt.where(Run.run_at >= window_start)
    stmt = stmt.where(Run.run_at <= window_end)
    return list(db.scalars(stmt))


def recompute_scores(
    db: Session,
    brand_id: uuid.UUID,
    engine_key: str = "openai",
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> dict:
    """Recompute and upsert one Score row for the given window (default all-time)."""
    from app.models import Score  # local import avoids a cycle at module load

    brand = db.get(Brand, brand_id)
    if brand is None:
        raise ValueError(f"brand {brand_id} not found")
    engine = db.scalar(select(Engine).where(Engine.key == engine_key))
    if engine is None:
        raise ValueError(f"engine {engine_key!r} not seeded")

    window_end = window_end or datetime.now(timezone.utc)
    run_ids = _run_ids_in_window(db, brand_id, engine.id, window_start, window_end)
    comp = compute_components(db, brand, run_ids)

    # Upsert on (brand, engine, window). window_start=None -> epoch sentinel so the
    # unique constraint has a concrete value for the all-time window.
    ws = window_start or datetime(1970, 1, 1, tzinfo=timezone.utc)
    existing = db.scalar(
        select(Score).where(
            Score.brand_id == brand_id,
            Score.engine_id == engine.id,
            Score.window_start == ws,
            Score.window_end == window_end,
        )
    )
    if existing is None:
        existing = Score(
            brand_id=brand_id, engine_id=engine.id, window_start=ws, window_end=window_end
        )
        db.add(existing)
    existing.visibility_score = comp.visibility_score
    existing.share_of_voice = comp.share_of_voice
    existing.mention_rate = comp.mention_rate
    existing.citation_rate = comp.citation_rate
    db.flush()

    return {
        "total_runs": comp.total_runs,
        "visibility_score": comp.visibility_score,
        "share_of_voice": comp.share_of_voice,
        "mention_rate": comp.mention_rate,
        "citation_rate": comp.citation_rate,
        "prominence_weight": comp.prominence_weight,
    }
