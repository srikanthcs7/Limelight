"""Brand + competitor detection over an answer's text.

M1 = fuzzy/substring matching only. M3 adds an LLM extraction pass on top for
recall + sentiment. Both produce the same `DetectedMention` shape, so the runner
and scoring don't change when M3 lands.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from rapidfuzz import fuzz

from app.logging_config import log_event

log = logging.getLogger("limelight.detection")

# A fuzzy match anywhere in the text at or above this partial-ratio counts as a
# mention even when there's no exact substring (catches spacing/casing variants).
FUZZY_THRESHOLD = 90


@dataclass
class Entity:
    name: str
    aliases: list[str]
    is_tracked_brand: bool


@dataclass
class DetectedMention:
    entity_type: str  # 'brand' | 'competitor'
    entity_name: str
    is_tracked_brand: bool
    position: int | None
    prominence: float | None
    sentiment: str | None = None  # 'positive' | 'neutral' | 'negative'


def _earliest_index(text_lower: str, entity: Entity) -> int | None:
    """Character index of the earliest surface form of the entity, or None.

    Tries exact case-insensitive substring first (gives a real position); falls
    back to a whole-text fuzzy check (mention with unknown position)."""
    surfaces = [entity.name, *entity.aliases]
    best: int | None = None
    for surface in surfaces:
        s = surface.strip().lower()
        if not s:
            continue
        idx = text_lower.find(s)
        if idx != -1 and (best is None or idx < best):
            best = idx
    if best is not None:
        return best
    # No exact hit — fuzzy fallback marks presence but not position.
    for surface in surfaces:
        if surface and fuzz.partial_ratio(surface.lower(), text_lower) >= FUZZY_THRESHOLD:
            return len(text_lower)  # sentinel: found, but after all exact matches
    return None


def _prominence(position: int) -> float:
    """1st-listed weighs most; decays with rank. Refined in M3."""
    return round(1.0 / position, 4)


def detect_mentions(answer_text: str, entities: list[Entity]) -> list[DetectedMention]:
    """Return mentions ordered by first appearance, with 1-based positions."""
    text_lower = answer_text.lower()
    hits: list[tuple[int, Entity]] = []
    for entity in entities:
        idx = _earliest_index(text_lower, entity)
        if idx is not None:
            hits.append((idx, entity))

    hits.sort(key=lambda h: h[0])
    mentions: list[DetectedMention] = []
    for rank, (_, entity) in enumerate(hits, start=1):
        mentions.append(
            DetectedMention(
                entity_type="brand" if entity.is_tracked_brand else "competitor",
                entity_name=entity.name,
                is_tracked_brand=entity.is_tracked_brand,
                position=rank,
                prominence=_prominence(rank),
            )
        )
    return mentions


# --- LLM extraction pass (M3) --------------------------------------------------------

_EXTRACT_SYSTEM = (
    "You extract brand/product/company mentions from an AI assistant's answer. "
    "List EVERY brand or product named, in order of first appearance, with a "
    "1-based position and the sentiment the answer expresses toward it "
    "(positive, neutral, or negative). Return STRICT JSON only."
)


def _match_tracked(name: str, entities: list[Entity]) -> Entity | None:
    n = name.strip().lower()
    for e in entities:
        if n == e.name.lower() or n in {a.lower() for a in e.aliases}:
            return e
    # loose containment (e.g. "the GetQuizSolve extension" -> GetQuizSolve)
    for e in entities:
        if e.name.lower() in n or n in e.name.lower():
            return e
    return None


def extract_with_llm(answer_text: str, entities: list[Entity]) -> list[DetectedMention]:
    """LLM extraction: every named brand, ordered, with sentiment. Tracked entities
    are canonicalised; others become untracked competitor mentions. Raises on
    failure so `detect` can fall back to fuzzy."""
    from app import llm

    tracked_names = [e.name for e in entities]
    user = (
        f"Answer:\n{answer_text}\n\n"
        f"Entities we track (canonical names): {tracked_names}\n\n"
        'Return JSON: {"mentions": [{"name": "...", "position": 1, '
        '"sentiment": "positive|neutral|negative"}]}'
    )
    raw = llm.complete_json(_EXTRACT_SYSTEM, user)

    mentions: list[DetectedMention] = []
    seen: set[str] = set()
    for m in raw.get("mentions", []) or []:
        name = (m.get("name") or "").strip()
        if not name:
            continue
        position = m.get("position")
        sentiment = (m.get("sentiment") or "neutral").strip().lower()
        if sentiment not in {"positive", "neutral", "negative"}:
            sentiment = "neutral"
        tracked = _match_tracked(name, entities)
        canonical = tracked.name if tracked else name
        if canonical.lower() in seen:
            continue
        seen.add(canonical.lower())
        mentions.append(
            DetectedMention(
                entity_type="brand" if (tracked and tracked.is_tracked_brand) else "competitor",
                entity_name=canonical,
                is_tracked_brand=bool(tracked and tracked.is_tracked_brand),
                position=int(position) if isinstance(position, int) else None,
                prominence=None,
                sentiment=sentiment,
            )
        )

    # Re-rank sequentially by the LLM's ordering (fall back to input order).
    mentions.sort(key=lambda m: (m.position is None, m.position or 0))
    for rank, m in enumerate(mentions, start=1):
        m.position = rank
        m.prominence = _prominence(rank)
    return mentions


def detect(answer_text: str, entities: list[Entity], use_llm: bool = True) -> list[DetectedMention]:
    """Primary detection path: LLM extraction with a fuzzy fallback. Produces the
    same DetectedMention shape the runner/scoring already consume."""
    if not answer_text.strip():
        return []
    if use_llm:
        try:
            mentions = extract_with_llm(answer_text, entities)
            if mentions:
                return mentions
        except Exception as exc:  # noqa: BLE001
            log_event(
                log, "detection.llm_failed", level=logging.WARNING, error=str(exc)
            )
    return detect_mentions(answer_text, entities)
