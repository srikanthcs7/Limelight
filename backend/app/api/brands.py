"""Brand read endpoints. Runs/scores/gaps routers are added in later milestones."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db import get_db
from app.models import Brand
from app.providers.registry import provider_keys
from app.schemas import BrandOut, BrandSettingsUpdate

router = APIRouter(prefix="/brands", tags=["brands"])

VALID_FREQUENCIES = {"manual", "hourly", "daily", "weekly"}


@router.get("", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db)) -> list[Brand]:
    return list(db.scalars(select(Brand).order_by(Brand.created_at)))


@router.get("/{brand_id}", response_model=BrandOut)
def get_brand(brand_id: uuid.UUID, db: Session = Depends(get_db)) -> Brand:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")
    return brand


@router.patch("/{brand_id}/settings", response_model=BrandOut, dependencies=[Depends(require_admin)])
def update_settings(
    brand_id: uuid.UUID, body: BrandSettingsUpdate, db: Session = Depends(get_db)
) -> Brand:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")

    if body.tracked_engines is not None:
        valid = set(provider_keys())
        chosen = [e for e in body.tracked_engines if e in valid]
        if not chosen:
            raise HTTPException(status_code=400, detail=f"tracked_engines must be a subset of {sorted(valid)}")
        brand.tracked_engines = chosen
    if body.run_frequency is not None:
        if body.run_frequency not in VALID_FREQUENCIES:
            raise HTTPException(status_code=400, detail=f"run_frequency must be one of {sorted(VALID_FREQUENCIES)}")
        brand.run_frequency = body.run_frequency
    if body.location is not None:
        brand.location = body.location or None
    if body.language is not None:
        brand.language = body.language

    db.commit()
    return brand


@router.get("/meta/engines")
def available_engines() -> dict:
    """The engine keys the server has providers for (drives the settings UI)."""
    return {"engines": provider_keys()}
