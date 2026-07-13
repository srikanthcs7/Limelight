"""Gap analysis (M6).

- Prompt gaps: prompts where competitors show up in ChatGPT's answer and the
  tracked brand does not — ranked losing-first.
- Source gaps: domains ChatGPT keeps citing → where to go get mentioned.
- Recommendations: an LLM pass that turns the gaps into concrete next actions
  (descriptive for Phase 1; the asset-generating "action layer" is roadmap).
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.logging_config import log_event
from app.models import Brand
from app.pipeline.analytics import prompt_breakdown, top_sources

log = logging.getLogger("limelight.gaps")


def prompt_gaps(db: Session, brand_id: uuid.UUID) -> list[dict]:
    """Prompts where a competitor is named but the brand isn't."""
    return [
        r
        for r in prompt_breakdown(db, brand_id)
        if not r["brand_mentioned"] and r["competitors_present"]
    ]


def source_gaps(db: Session, brand_id: uuid.UUID, limit: int = 10) -> list[dict]:
    """Domains ChatGPT cites most — outreach/placement targets."""
    return top_sources(db, brand_id, limit)


def compute_gaps(db: Session, brand_id: uuid.UUID) -> dict:
    """Cheap (no LLM) gap report."""
    return {
        "prompt_gaps": prompt_gaps(db, brand_id),
        "source_gaps": source_gaps(db, brand_id),
    }


def recommend(db: Session, brand_id: uuid.UUID) -> list[str]:
    """LLM pass: turn the gaps into a short ranked list of concrete actions."""
    from app import llm

    brand = db.get(Brand, brand_id)
    if brand is None:
        raise ValueError(f"brand {brand_id} not found")
    gaps = compute_gaps(db, brand_id)

    losing = [
        {"prompt": g["text"], "competitors": g["competitors_present"][:4]}
        for g in gaps["prompt_gaps"][:15]
    ]
    sources = [s["domain"] for s in gaps["source_gaps"][:10]]

    if not losing and not sources:
        return []

    system = (
        "You advise a brand on improving its visibility in AI assistant answers "
        "(GEO/AEO). Given prompts where the brand is absent but competitors appear, "
        "and the domains the assistant cites most, propose concrete, specific next "
        "actions (content to create, places to get mentioned, comparisons to publish). "
        "Return STRICT JSON."
    )
    user = (
        f"Brand: {brand.display_name} ({brand.domain}) — {brand.category or 'unknown category'}\n"
        f"Prompts where we're absent but competitors appear:\n{losing}\n\n"
        f"Domains the assistant cites most:\n{sources}\n\n"
        'Return JSON: {"recommendations": ["action 1", "action 2", ...]} '
        "(5-7 items, each one concrete sentence)."
    )
    raw = llm.complete_json(system, user)
    recs = [r.strip() for r in raw.get("recommendations", []) if isinstance(r, str) and r.strip()]
    log_event(log, "gaps.recommend", brand_id=str(brand_id), recommendations=len(recs))
    return recs
