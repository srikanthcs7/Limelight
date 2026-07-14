"""Dashboard aggregation endpoints (read-only). All accept an `engine` query
param (default openai) so the dashboard can view any tracked engine."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.pipeline import analytics

router = APIRouter(prefix="/brands/{brand_id}", tags=["analytics"])


@router.get("/share-of-voice")
def share_of_voice(brand_id: uuid.UUID, engine: str = "openai", db: Session = Depends(get_db)) -> list[dict]:
    return analytics.share_of_voice(db, brand_id, engine)


@router.get("/sources")
def sources(
    brand_id: uuid.UUID, engine: str = "openai", limit: int = 15, db: Session = Depends(get_db)
) -> list[dict]:
    return analytics.top_sources(db, brand_id, limit, engine)


@router.get("/prompt-breakdown")
def prompt_breakdown(brand_id: uuid.UUID, engine: str = "openai", db: Session = Depends(get_db)) -> list[dict]:
    return analytics.prompt_breakdown(db, brand_id, engine)


@router.get("/intent-coverage")
def intent_coverage(brand_id: uuid.UUID, engine: str = "openai", db: Session = Depends(get_db)) -> list[dict]:
    return analytics.intent_coverage(db, brand_id, engine)


@router.get("/share-of-voice/timeline")
def sov_timeline(brand_id: uuid.UUID, engine: str = "openai", db: Session = Depends(get_db)) -> dict:
    return analytics.sov_timeline(db, brand_id, engine_key=engine)
