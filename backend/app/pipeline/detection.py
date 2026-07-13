"""Brand + competitor detection over an answer's text.

M1 = fuzzy/substring matching only. M3 adds an LLM extraction pass on top for
recall + sentiment. Both produce the same `DetectedMention` shape, so the runner
and scoring don't change when M3 lands.
"""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

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
