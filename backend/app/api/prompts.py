"""Prompt endpoints: list (open) + generate (admin-gated)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db import get_db
from app.models import Prompt
from app.pipeline.prompt_gen import DEFAULT_TARGET
from app.schemas import PromptOut

router = APIRouter(prefix="/brands/{brand_id}/prompts", tags=["prompts"])


class PromptUpdate(BaseModel):
    text: str | None = None
    active: bool | None = None


class PromptIds(BaseModel):
    prompt_ids: list[uuid.UUID]


@router.get("", response_model=list[PromptOut])
def list_prompts(
    brand_id: uuid.UUID, active_only: bool = False, db: Session = Depends(get_db)
) -> list[Prompt]:
    stmt = select(Prompt).where(Prompt.brand_id == brand_id)
    if active_only:
        stmt = stmt.where(Prompt.active.is_(True))
    return list(db.scalars(stmt.order_by(Prompt.created_at)))


@router.post(":generate", dependencies=[Depends(require_admin)])
def generate_prompts(
    brand_id: uuid.UUID, target: int = DEFAULT_TARGET, db: Session = Depends(get_db)
) -> dict:
    """Scrape the domain + generate buyer prompts (admin-gated; makes an LLM call)."""
    from app.pipeline.prompt_gen import generate_for_brand

    summary = generate_for_brand(db, brand_id, target=target)
    db.commit()
    return summary


@router.post(":refine", dependencies=[Depends(require_admin)])
def refine_selected(brand_id: uuid.UUID, body: PromptIds, db: Session = Depends(get_db)) -> dict:
    """LLM-refine the selected prompts in place (admin-gated; makes an LLM call)."""
    from app.pipeline.prompt_gen import refine_prompts

    result = refine_prompts(db, brand_id, body.prompt_ids)
    db.commit()
    return result


@router.post(":bulk-delete", dependencies=[Depends(require_admin)])
def bulk_delete(brand_id: uuid.UUID, body: PromptIds, db: Session = Depends(get_db)) -> dict:
    """Delete the selected prompts (soft-delete any that have run history)."""
    from app.models import Run

    deleted = deactivated = 0
    for pid in body.prompt_ids:
        prompt = db.get(Prompt, pid)
        if prompt is None or prompt.brand_id != brand_id:
            continue
        if db.scalar(select(Run.id).where(Run.prompt_id == pid).limit(1)) is not None:
            prompt.active = False
            deactivated += 1
        else:
            db.delete(prompt)
            deleted += 1
    db.commit()
    return {"deleted": deleted, "deactivated": deactivated}


def _get_prompt(db: Session, brand_id: uuid.UUID, prompt_id: uuid.UUID) -> Prompt:
    prompt = db.get(Prompt, prompt_id)
    if prompt is None or prompt.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="prompt not found")
    return prompt


@router.patch("/{prompt_id}", response_model=PromptOut, dependencies=[Depends(require_admin)])
def update_prompt(
    brand_id: uuid.UUID,
    prompt_id: uuid.UUID,
    body: PromptUpdate,
    db: Session = Depends(get_db),
) -> Prompt:
    prompt = _get_prompt(db, brand_id, prompt_id)
    if body.text is not None:
        prompt.text = body.text.strip()
    if body.active is not None:
        prompt.active = body.active
    db.commit()
    return prompt


@router.delete("/{prompt_id}", dependencies=[Depends(require_admin)])
def delete_prompt(
    brand_id: uuid.UUID, prompt_id: uuid.UUID, db: Session = Depends(get_db)
) -> dict:
    """Hard-delete a prompt with no runs; otherwise soft-delete (deactivate) so its
    run history is preserved."""
    from app.models import Run

    prompt = _get_prompt(db, brand_id, prompt_id)
    run_exists = db.scalar(select(Run.id).where(Run.prompt_id == prompt_id).limit(1)) is not None
    if run_exists:
        prompt.active = False
        db.commit()
        return {"deleted": False, "deactivated": True}
    db.delete(prompt)
    db.commit()
    return {"deleted": True, "deactivated": False}
