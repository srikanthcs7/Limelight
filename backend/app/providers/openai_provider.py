"""OpenAI / ChatGPT engine adapter (Tier 2: Responses API + web_search tool).

M0 defines the class and the extraction seam; M1 fills in the real API call and
confirms the exact Responses API response shape (url_citation annotations +
sources list).
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import tldextract

from app.config import get_settings
from app.providers.base import CitedUrl, EngineResult


def domain_of(url: str) -> str:
    """Registrable domain for a URL (e.g. https://a.b.example.com/x -> example.com)."""
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    # Fallback to the netloc if tldextract can't resolve a suffix.
    return urlparse(url).netloc or url


class OpenAIProvider:
    key = "openai"

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.openai_engine_model
        self._api_key = settings.openai_api_key

    def run(self, prompt: str, opts: dict[str, Any] | None = None) -> EngineResult:
        # Implemented in M1 (vertical slice) against the live Responses API.
        raise NotImplementedError("OpenAIProvider.run is implemented in M1")
