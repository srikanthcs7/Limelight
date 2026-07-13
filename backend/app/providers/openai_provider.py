"""OpenAI / ChatGPT engine adapter — Tier 2: Responses API + web_search tool.

The call returns the same search-grounded model ChatGPT search uses, with real
inline citations (`url_citation` annotations) plus the sources it browsed.

Extraction is split into a pure `extract_engine_result(raw_dict)` helper so it can
be unit-tested against fixtures without a live API call. `run()` makes the SDK
call, dumps the response to a dict, and hands it to the helper.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import tldextract

from app.config import get_settings
from app.providers.base import CitedUrl, EngineResult


def domain_of(url: str) -> str:
    """Registrable domain for a URL (https://a.b.example.com/x -> example.com)."""
    ext = tldextract.extract(url)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return urlparse(url).netloc or url


def _answer_text(raw: dict[str, Any]) -> str:
    """`output_text` if the dump carries it; else concat message output_text parts."""
    if raw.get("output_text"):
        return raw["output_text"]
    parts: list[str] = []
    for item in raw.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts)


def _cited_urls(raw: dict[str, Any]) -> list[CitedUrl]:
    """Collect url_citation annotations from message content (first-seen order)."""
    urls: list[CitedUrl] = []
    for item in raw.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            for ann in content.get("annotations", []) or []:
                if ann.get("type") == "url_citation" and ann.get("url"):
                    urls.append(CitedUrl(url=ann["url"], domain=domain_of(ann["url"])))
    return urls


def extract_engine_result(raw: dict[str, Any]) -> EngineResult:
    return EngineResult(answer_text=_answer_text(raw), cited_urls=_cited_urls(raw), raw=raw)


class OpenAIProvider:
    key = "openai"

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.openai_engine_model
        self._api_key = settings.openai_api_key

    def run(self, prompt: str, opts: dict[str, Any] | None = None) -> EngineResult:
        # Imported lazily so the module (and the whole app) loads without the
        # SDK configured — only an actual run needs a key + network egress.
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.responses.create(
            model=self._model,
            input=prompt,
            tools=[{"type": "web_search"}],
            tool_choice="auto",
        )
        return extract_engine_result(response.model_dump())
