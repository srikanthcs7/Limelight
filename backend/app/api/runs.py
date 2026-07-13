"""Run read endpoints (engine-agnostic — never references a provider)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Prompt, Run
from app.schemas import RunOut

router = APIRouter(prefix="/brands/{brand_id}/runs", tags=["runs"])


@router.get("", response_model=list[RunOut])
def list_runs(brand_id: uuid.UUID, limit: int = 50, db: Session = Depends(get_db)) -> list[Run]:
    prompt_ids = list(db.scalars(select(Prompt.id).where(Prompt.brand_id == brand_id)))
    if not prompt_ids:
        return []
    return list(
        db.scalars(
            select(Run)
            .where(Run.prompt_id.in_(prompt_ids))
            .options(selectinload(Run.mentions), selectinload(Run.citations))
            .order_by(Run.run_at.desc())
            .limit(limit)
        )
    )
