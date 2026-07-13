"""Normalize an engine's cited URLs into citation records (dedup by URL)."""
from __future__ import annotations

from app.providers.base import CitedUrl


def dedupe_citations(cited_urls: list[CitedUrl]) -> list[CitedUrl]:
    """Drop duplicate URLs, preserving first-seen order."""
    seen: set[str] = set()
    out: list[CitedUrl] = []
    for c in cited_urls:
        if c.url in seen:
            continue
        seen.add(c.url)
        out.append(c)
    return out
