"""OpenAI / ChatGPT engine adapter — Tier 2: Responses API + web_search tool.

The call returns the same search-grounded model ChatGPT search uses, with real
inline citations (`url_citation` annotations) plus the sources it browsed.

Extraction is split into a pure `extract_engine_result(raw_dict)` helper so it can
be unit-tested against fixtures without a live API call. `run()` makes the SDK
call, dumps the response to a dict, and hands it to the helper.
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.logging_config import log_event
from app.providers.base import CitedUrl, EngineResult, domain_of

log = logging.getLogger("limelight.provider.openai")

__all__ = ["OpenAIProvider", "extract_engine_result", "domain_of"]

# Nudges the model to actually search + ground its answer, so runs carry real
# citations rather than answering from training memory.
GROUNDING_INSTRUCTIONS = (
    "You are answering as a current, web-connected AI assistant. Use the web "
    "search tool to find up-to-date information and base your answer on real "
    "sources you looked up."
)


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
    """Collect cited URLs (first-seen order) from two places:
    1. `url_citation` annotations on the assistant message content, and
    2. any `sources`/`results` carried on a `web_search_call` item (defensive —
       shape varies across SDK versions)."""
    urls: list[CitedUrl] = []

    def add(u: str | None) -> None:
        if u:
            urls.append(CitedUrl(url=u, domain=domain_of(u)))

    for item in raw.get("output", []) or []:
        itype = item.get("type")
        if itype == "message":
            for content in item.get("content", []) or []:
                for ann in content.get("annotations", []) or []:
                    if ann.get("type") == "url_citation":
                        add(ann.get("url"))
        elif itype == "web_search_call":
            action = item.get("action") or {}
            for src in (action.get("sources") or item.get("sources") or item.get("results") or []):
                if isinstance(src, dict):
                    add(src.get("url"))
    return urls


def diagnostics(raw: dict[str, Any]) -> dict[str, Any]:
    """Summary of what the API actually returned — logged so we can see whether
    web_search fired and citations came back, without dumping the full payload."""
    output = raw.get("output", []) or []
    item_types = [i.get("type") for i in output]
    annotations = 0
    for item in output:
        if item.get("type") == "message":
            for content in item.get("content", []) or []:
                annotations += len(content.get("annotations", []) or [])
    return {
        "output_item_types": item_types,
        "web_search_invoked": "web_search_call" in item_types,
        "annotation_count": annotations,
    }


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
            instructions=GROUNDING_INSTRUCTIONS,
            tools=[{"type": "web_search"}],
            tool_choice="auto",
        )
        raw = response.model_dump()
        result = extract_engine_result(raw)
        log_event(
            log,
            "provider.openai.run",
            model=self._model,
            prompt_preview=prompt[:120],
            answer_len=len(result.answer_text),
            citations=len(result.cited_urls),
            **diagnostics(raw),
        )
        return result
