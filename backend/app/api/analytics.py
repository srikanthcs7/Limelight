"""Dashboard aggregation endpoints (read-only)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.pipeline import analytics

router = APIRouter(prefix="/brands/{brand_id}", tags=["analytics"])


@router.get("/share-of-voice")
def share_of_voice(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    return analytics.share_of_voice(db, brand_id)


@router.get("/sources")
def sources(brand_id: uuid.UUID, limit: int = 15, db: Session = Depends(get_db)) -> list[dict]:
    return analytics.top_sources(db, brand_id, limit)


@router.get("/prompt-breakdown")
def prompt_breakdown(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    return analytics.prompt_breakdown(db, brand_id)
