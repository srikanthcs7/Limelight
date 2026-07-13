"""Prompt endpoints: list (open) + generate (admin-gated)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db import get_db
from app.models import Prompt
from app.schemas import PromptOut

router = APIRouter(prefix="/brands/{brand_id}/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptOut])
def list_prompts(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Prompt]:
    return list(
        db.scalars(
            select(Prompt).where(Prompt.brand_id == brand_id).order_by(Prompt.created_at)
        )
    )


@router.post(":generate", dependencies=[Depends(require_admin)])
def generate_prompts(brand_id: uuid.UUID, target: int = 60, db: Session = Depends(get_db)) -> dict:
    """Scrape the domain + generate buyer prompts (admin-gated; makes an LLM call)."""
    from app.pipeline.prompt_gen import generate_for_brand

    summary = generate_for_brand(db, brand_id, target=target)
    db.commit()
    return summary
