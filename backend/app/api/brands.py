"""Brand read endpoints. Runs/scores/gaps routers are added in later milestones."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Brand
from app.schemas import BrandOut

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db)) -> list[Brand]:
    return list(db.scalars(select(Brand).order_by(Brand.created_at)))


@router.get("/{brand_id}", response_model=BrandOut)
def get_brand(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> Brand:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")
    return brand
