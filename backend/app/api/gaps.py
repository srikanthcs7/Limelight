"""Gap endpoints: gaps (open, cheap) + recommendations (admin-gated, LLM)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db import get_db
from app.pipeline import gaps as gaps_mod

router = APIRouter(prefix="/brands/{brand_id}/gaps", tags=["gaps"])


@router.get("")
def get_gaps(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return gaps_mod.compute_gaps(db, brand_id)


@router.post("/recommend", dependencies=[Depends(require_admin)])
def recommend(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return {"recommendations": gaps_mod.recommend(db, brand_id)}
