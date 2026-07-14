"""Run read endpoints (engine-agnostic — never references a provider)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_admin
from app.db import get_db
from app.models import Engine, Prompt, Run
from app.pipeline.runner import run_brand_all_engines
from app.pipeline.scoring import recompute_all_engines
from app.schemas import RunOut

router = APIRouter(prefix="/brands/{brand_id}/runs", tags=["runs"])


@router.get("", response_model=list[RunOut])
def list_runs(
    brand_id: uuid.UUID, engine: str = "openai", limit: int = 50, db: Session = Depends(get_db)
) -> list[Run]:
    prompt_ids = list(db.scalars(select(Prompt.id).where(Prompt.brand_id == brand_id)))
    if not prompt_ids:
        return []
    stmt = select(Run).where(Run.prompt_id.in_(prompt_ids))
    engine_id = db.scalar(select(Engine.id).where(Engine.key == engine))
    if engine_id is not None:
        stmt = stmt.where(Run.engine_id == engine_id)
    return list(
        db.scalars(
            stmt.options(selectinload(Run.mentions), selectinload(Run.citations))
            .order_by(Run.run_at.desc())
            .limit(limit)
        )
    )


@router.get("/{run_id}")
def get_run(brand_id: uuid.UUID, run_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Full run incl. the complete stored provider response (raw_response_json)."""
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    brand_of_run = db.scalar(select(Prompt.brand_id).where(Prompt.id == run.prompt_id))
    if brand_of_run != brand_id:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "id": str(run.id),
        "run_at": run.run_at.isoformat(),
        "answer_text": run.answer_text,
        "raw_response_json": run.raw_response_json,
    }


@router.post("", status_code=201, dependencies=[Depends(require_admin)])
def trigger_run(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Run all active prompts through each of the brand's tracked engines now
    (synchronous). Protected by the admin token; bulk scheduling is the Celery
    path (M4/P2.2)."""
    per_engine = run_brand_all_engines(db, brand_id)
    db.flush()
    recompute_all_engines(db, brand_id)
    db.commit()
    return {"runs": sum(per_engine.values()), "by_engine": per_engine}
