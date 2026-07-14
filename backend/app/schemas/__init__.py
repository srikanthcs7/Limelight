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
    tracked_engines: list[str]
    run_frequency: str
    location: str | None
    language: str
    last_run_at: datetime | None
    competitors: list[CompetitorOut] = []


class BrandSettingsUpdate(BaseModel):
    tracked_engines: list[str] | None = None
    run_frequency: str | None = None
    location: str | None = None
    language: str | None = None


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    intent_type: str | None
    active: bool
    created_at: datetime


class MentionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_type: str
    entity_name: str
    is_tracked_brand: bool
    position: int | None
    prominence: float | None
    sentiment: str | None


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    domain: str
    source_type: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt_id: uuid.UUID
    engine_id: int
    run_at: datetime
    answer_text: str
    mentions: list[MentionOut] = []
    citations: list[CitationOut] = []


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    window_label: str  # 'all' | '7d' | '30d'
    window_start: datetime
    window_end: datetime
    visibility_score: float
    share_of_voice: float
    mention_rate: float
    citation_rate: float
    computed_at: datetime
