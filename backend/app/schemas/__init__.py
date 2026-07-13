"""Pydantic response models for the API."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    aliases: list[str]
    domain: str | None


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    display_name: str
    aliases: list[str]
    category: str | None
    created_at: datetime
    competitors: list[CompetitorOut] = []
