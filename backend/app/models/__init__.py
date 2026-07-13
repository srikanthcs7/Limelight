"""SQLAlchemy models (spec §6). `runs` are append-only/immutable; `scores` are
recomputed per window."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = _uuid_pk()
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    category: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competitors: Mapped[list["Competitor"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )
    prompts: Mapped[list["Prompt"]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = _uuid_pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    domain: Mapped[str | None] = mapped_column(String(255))

    brand: Mapped[Brand] = relationship(back_populates="competitors")


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = _uuid_pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # 'best_of' | 'comparison' | 'alternatives' | 'problem_first'
    intent_type: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brand: Mapped[Brand] = relationship(back_populates="prompts")


class Engine(Base):
    __tablename__ = "engines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # 'openai' etc.


class Run(Base):
    """One execution of (prompt × engine) at a point in time. IMMUTABLE / append-only."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = _uuid_pk()
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prompts.id", ondelete="CASCADE"), index=True
    )
    engine_id: Mapped[int] = mapped_column(ForeignKey("engines.id"), index=True)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, default="")
    raw_response_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    mentions: Mapped[list["Mention"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Mention(Base):
    __tablename__ = "mentions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32))  # 'brand' | 'competitor'
    entity_name: Mapped[str] = mapped_column(String(255))
    is_tracked_brand: Mapped[bool] = mapped_column(Boolean, default=False)
    # 1-based rank of first appearance in the answer (1 = named first). Null if unknown.
    position: Mapped[int | None] = mapped_column(Integer)
    # 0..1 prominence weight derived from position/emphasis.
    prominence: Mapped[float | None] = mapped_column(Float)
    sentiment: Mapped[str | None] = mapped_column(String(32))

    run: Mapped[Run] = relationship(back_populates="mentions")


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    source_type: Mapped[str | None] = mapped_column(String(64))

    run: Mapped[Run] = relationship(back_populates="citations")


class Score(Base):
    """Recomputed per window from runs — never a source of truth, always derived."""

    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint(
            "brand_id", "engine_id", "window_start", "window_end", name="uq_score_window"
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), index=True
    )
    engine_id: Mapped[int] = mapped_column(ForeignKey("engines.id"), index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    visibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    share_of_voice: Mapped[float] = mapped_column(Float, default=0.0)
    mention_rate: Mapped[float] = mapped_column(Float, default=0.0)
    citation_rate: Mapped[float] = mapped_column(Float, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


__all__ = [
    "Brand",
    "Competitor",
    "Prompt",
    "Engine",
    "Run",
    "Mention",
    "Citation",
    "Score",
]
