"""Read-side aggregations for the dashboard: competitor share-of-voice, top
cited sources, and per-prompt breakdown. All computed from immutable runs."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Citation, Engine, Mention, Prompt, Run

DEFAULT_ENGINE = "openai"


def _brand_run_ids(db: Session, brand_id: uuid.UUID, engine_key: str = DEFAULT_ENGINE) -> list[uuid.UUID]:
    prompt_ids = list(db.scalars(select(Prompt.id).where(Prompt.brand_id == brand_id)))
    if not prompt_ids:
        return []
    stmt = select(Run.id).where(Run.prompt_id.in_(prompt_ids))
    engine_id = db.scalar(select(Engine.id).where(Engine.key == engine_key))
    if engine_id is not None:
        stmt = stmt.where(Run.engine_id == engine_id)
    return list(db.scalars(stmt))


def _sentiment_count(value: str):
    return func.count().filter(Mention.sentiment == value)


def share_of_voice(db: Session, brand_id: uuid.UUID, engine_key: str = DEFAULT_ENGINE) -> list[dict]:
    """Mentions per entity across the brand's runs, with share + sentiment split."""
    run_ids = _brand_run_ids(db, brand_id, engine_key)
    if not run_ids:
        return []
    rows = db.execute(
        select(
            Mention.entity_name,
            func.bool_or(Mention.is_tracked_brand).label("is_tracked_brand"),
            func.count().label("mentions"),
            _sentiment_count("positive").label("positive"),
            _sentiment_count("neutral").label("neutral"),
            _sentiment_count("negative").label("negative"),
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
            "positive": r.positive,
            "neutral": r.neutral,
            "negative": r.negative,
        }
        for r in rows
    ]


def intent_coverage(db: Session, brand_id: uuid.UUID, engine_key: str = DEFAULT_ENGINE) -> list[dict]:
    """Per intent type: how many active prompts mention the brand (coverage)."""
    rows = prompt_breakdown(db, brand_id, engine_key)
    buckets: dict[str, dict] = {}
    for r in rows:
        key = r["intent_type"] or "other"
        b = buckets.setdefault(key, {"intent_type": key, "total": 0, "mentioned": 0})
        b["total"] += 1
        if r["brand_mentioned"]:
            b["mentioned"] += 1
    out = list(buckets.values())
    for b in out:
        b["coverage"] = round(b["mentioned"] / b["total"], 4) if b["total"] else 0.0
    out.sort(key=lambda b: b["intent_type"])
    return out


def sov_timeline(
    db: Session, brand_id: uuid.UUID, top: int = 4, engine_key: str = DEFAULT_ENGINE
) -> dict:
    """Per-day share of voice for the brand + top competitors (rest folded into
    'Other'). Builds a multi-series trend from immutable runs."""
    run_ids = _brand_run_ids(db, brand_id, engine_key)
    if not run_ids:
        return {"days": [], "series": []}
    day = func.date(Run.run_at).label("day")
    rows = db.execute(
        select(day, Mention.entity_name, func.bool_or(Mention.is_tracked_brand), func.count())
        .join(Run, Run.id == Mention.run_id)
        .where(Mention.run_id.in_(run_ids))
        .group_by(day, Mention.entity_name)
    ).all()

    days = sorted({str(r[0]) for r in rows})
    totals_by_day: dict[str, int] = {}
    per_entity: dict[str, dict] = {}  # name -> {is_tracked, total, by_day{day:count}}
    for d, name, is_tracked, cnt in rows:
        d = str(d)
        totals_by_day[d] = totals_by_day.get(d, 0) + cnt
        e = per_entity.setdefault(name, {"is_tracked": is_tracked, "total": 0, "by_day": {}})
        e["total"] += cnt
        e["by_day"][d] = e["by_day"].get(d, 0) + cnt

    brand_names = [n for n, e in per_entity.items() if e["is_tracked"]]
    competitors = sorted(
        (n for n, e in per_entity.items() if not e["is_tracked"]),
        key=lambda n: per_entity[n]["total"],
        reverse=True,
    )
    keep = brand_names + competitors[:top]
    other = competitors[top:]

    def series_points(names: list[str]) -> list[float]:
        pts = []
        for d in days:
            num = sum(per_entity[n]["by_day"].get(d, 0) for n in names)
            denom = totals_by_day.get(d, 0) or 1
            pts.append(round(num / denom, 4))
        return pts

    series = [
        {"name": n, "is_tracked_brand": per_entity[n]["is_tracked"], "points": series_points([n])}
        for n in keep
    ]
    if other:
        series.append({"name": "Other", "is_tracked_brand": False, "points": series_points(other)})
    return {"days": days, "series": series}


def top_sources(
    db: Session, brand_id: uuid.UUID, limit: int = 15, engine_key: str = DEFAULT_ENGINE
) -> list[dict]:
    """Domains the engine cites most across the brand's runs."""
    run_ids = _brand_run_ids(db, brand_id, engine_key)
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


def prompt_breakdown(db: Session, brand_id: uuid.UUID, engine_key: str = DEFAULT_ENGINE) -> list[dict]:
    """Per active prompt: latest-run brand mention status + run count for one
    engine. Powers the drill-down and the gap list."""
    engine_id = db.scalar(select(Engine.id).where(Engine.key == engine_key))
    prompts = list(
        db.scalars(
            select(Prompt).where(Prompt.brand_id == brand_id, Prompt.active.is_(True))
        )
    )
    out: list[dict] = []
    for p in prompts:
        stmt = select(Run).where(Run.prompt_id == p.id)
        if engine_id is not None:
            stmt = stmt.where(Run.engine_id == engine_id)
        runs = list(db.scalars(stmt.order_by(Run.run_at.desc())))
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
