"""Admin write endpoints (gated by the ADMIN_TOKEN shared secret)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db import get_db
from app.models import Brand
from app.seed import seed_getquizsolve

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/seed")
def seed(db: Session = Depends(get_db)) -> dict:
    """Seed the GetQuizSolve brand (idempotent). Returns its id."""
    brand = seed_getquizsolve(db)
    db.commit()
    return {"brand_id": str(brand.id), "display_name": brand.display_name}


@router.get("/brand-count")
def brand_count(db: Session = Depends(get_db)) -> dict:
    """Cheap check the client uses to decide whether to offer 'Seed'."""
    return {"count": db.scalar(select(func.count()).select_from(Brand)) or 0}
