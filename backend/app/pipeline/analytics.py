"""Read-side aggregations for the dashboard: competitor share-of-voice, top
cited sources, and per-prompt breakdown. All computed from immutable runs."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Citation, Mention, Prompt, Run


def _brand_run_ids(db: Session, brand_id: uuid.UUID) -> list[uuid.UUID]:
    prompt_ids = list(db.scalars(select(Prompt.id).where(Prompt.brand_id == brand_id)))
    if not prompt_ids:
        return []
    return list(db.scalars(select(Run.id).where(Run.prompt_id.in_(prompt_ids))))


def share_of_voice(db: Session, brand_id: uuid.UUID) -> list[dict]:
    """Mentions per entity across the brand's runs, with each entity's share."""
    run_ids = _brand_run_ids(db, brand_id)
    if not run_ids:
        return []
    rows = db.execute(
        select(
            Mention.entity_name,
            func.bool_or(Mention.is_tracked_brand).label("is_tracked_brand"),
            func.count().label("mentions"),
        )
        .where(Mention.run_id.in_(run_ids))
        .group_by(Mention.entity_name)
        .order_by(func.count().desc())
    ).all()
    total = sum(r.mentions for r in rows) or 1
    return [
        {
            "entity_name": r.entity_name,
            "is_tracked_brand": r.is_tracked_brand,
            "mentions": r.mentions,
            "share": round(r.mentions / total, 4),
        }
        for r in rows
    ]


def top_sources(db: Session, brand_id: uuid.UUID, limit: int = 15) -> list[dict]:
    """Domains the engine cites most across the brand's runs."""
    run_ids = _brand_run_ids(db, brand_id)
    if not run_ids:
        return []
    rows = db.execute(
        select(Citation.domain, func.count().label("citations"))
        .where(Citation.run_id.in_(run_ids))
        .group_by(Citation.domain)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [{"domain": r.domain, "citations": r.citations} for r in rows]


def prompt_breakdown(db: Session, brand_id: uuid.UUID) -> list[dict]:
    """Per active prompt: latest-run brand mention status + run count. Powers the
    drill-down and (in M6) the gap list."""
    prompts = list(
        db.scalars(
            select(Prompt).where(Prompt.brand_id == brand_id, Prompt.active.is_(True))
        )
    )
    out: list[dict] = []
    for p in prompts:
        runs = list(
            db.scalars(select(Run).where(Run.prompt_id == p.id).order_by(Run.run_at.desc()))
        )
        latest = runs[0] if runs else None
        brand_mentioned = False
        position = None
        competitors_present: list[str] = []
        if latest is not None:
            mentions = list(db.scalars(select(Mention).where(Mention.run_id == latest.id)))
            for m in mentions:
                if m.is_tracked_brand:
                    brand_mentioned = True
                    position = m.position
                else:
                    competitors_present.append(m.entity_name)
        out.append(
            {
                "prompt_id": str(p.id),
                "text": p.text,
                "intent_type": p.intent_type,
                "runs_count": len(runs),
                "last_run_at": latest.run_at.isoformat() if latest else None,
                "brand_mentioned": brand_mentioned,
                "position": position,
                "competitors_present": competitors_present,
            }
        )
    # Losing prompts first (brand absent), then by fewest mentions.
    out.sort(key=lambda r: (r["brand_mentioned"], r["position"] or 999))
    return out
