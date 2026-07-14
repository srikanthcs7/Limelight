"""The engine boundary. Every AI surface implements EngineProvider and returns a
normalized EngineResult. Detection / scoring / storage / dashboard consume only
``{answer_text, cited_urls}`` and MUST NOT know which provider produced it.

Get this right and Phase 2 (Google AIO, Gemini) is "write two adapters," not a
rewrite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

import tldextract


def domain_of(url: str) -> str:
    """Registrable domain for a URL (https://a.b.example.com/x -> example.com)."""
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return urlparse(url).netloc or url


@dataclass
class CitedUrl:
    url: str
    domain: str


@dataclass
class EngineResult:
    answer_text: str
    cited_urls: list[CitedUrl] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)  # full provider response, stored on the run


@runtime_checkable
class EngineProvider(Protocol):
    key: str

    def run(self, prompt: str, opts: dict[str, Any] | None = None) -> EngineResult:
        """Query the engine with a single prompt and return a normalized result."""
        ...
