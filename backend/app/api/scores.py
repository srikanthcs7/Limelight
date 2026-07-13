"""Score read endpoints. Scores are derived; this recomputes the all-time window
on read for M1 (M3 adds stored rolling windows + a history series for the chart)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Score
from app.pipeline.scoring import recompute_scores
from app.schemas import ScoreOut

router = APIRouter(prefix="/brands/{brand_id}/scores", tags=["scores"])


@router.get("", response_model=list[ScoreOut])
def list_scores(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Score]:
    """Recompute the all-time window, then return all stored score rows (the
    series the trend chart reads)."""
    recompute_scores(db, brand_id)
    db.commit()
    return list(
        db.scalars(
            select(Score).where(Score.brand_id == brand_id).order_by(Score.window_end)
        )
    )
