"""Score read endpoints. Scores are derived; this recomputes the standard windows
(all / 30d / 7d) on read, then returns every stored row tagged with a window label
so the trend chart can pick a series."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Score
from app.pipeline.scoring import EPOCH, recompute_scores
from app.schemas import ScoreOut

router = APIRouter(prefix="/brands/{brand_id}/scores", tags=["scores"])


def _label(score: Score) -> str:
    if score.window_start <= EPOCH:
        return "all"
    days = round((score.window_end - score.window_start).total_seconds() / 86400)
    return f"{days}d"


@router.get("", response_model=list[ScoreOut])
def list_scores(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ScoreOut]:
    recompute_scores(db, brand_id)
    db.commit()
    rows = db.scalars(
        select(Score).where(Score.brand_id == brand_id).order_by(Score.window_end)
    )
    return [
        ScoreOut(
            window_label=_label(s),
            window_start=s.window_start,
            window_end=s.window_end,
            visibility_score=s.visibility_score,
            share_of_voice=s.share_of_voice,
            mention_rate=s.mention_rate,
            citation_rate=s.citation_rate,
            computed_at=s.computed_at,
        )
        for s in rows
    ]
