"""Google AI Overviews engine via SerpApi (Phase 2).

Google AI Overviews has no official API and is JS-rendered + geo-personalised, so
we read it through SerpApi's structured `ai_overview` result rather than scraping
Google ourselves. Same EngineProvider contract as OpenAI — everything downstream
is unchanged.

Parsing is split into a pure `extract_aio_result(raw)` helper so it's unit-tested
against fixtures; the exact live shape is confirmed in the user's environment
(like the OpenAI M1 checkpoint).
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.logging_config import log_event
from app.providers.base import CitedUrl, EngineResult, domain_of

log = logging.getLogger("limelight.provider.google_aio")

SERPAPI_URL = "https://serpapi.com/search.json"


def _answer_text(ai_overview: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in ai_overview.get("text_blocks", []) or []:
        btype = block.get("type")
        if block.get("snippet"):
            parts.append(block["snippet"])
        if btype == "list":
            for item in block.get("list", []) or []:
                seg = " ".join(x for x in [item.get("title"), item.get("snippet")] if x)
                if seg:
                    parts.append(f"- {seg}")
    return "\n".join(parts)


def _cited_urls(ai_overview: dict[str, Any]) -> list[CitedUrl]:
    urls: list[CitedUrl] = []
    for ref in ai_overview.get("references", []) or []:
        link = ref.get("link")
        if link:
            urls.append(CitedUrl(url=link, domain=domain_of(link)))
    return urls


def extract_aio_result(raw: dict[str, Any]) -> EngineResult:
    """Normalise a SerpApi Google response. If no AI Overview was shown, returns
    an empty answer (a valid 'not present' run)."""
    ai_overview = raw.get("ai_overview") or {}
    return EngineResult(
        answer_text=_answer_text(ai_overview),
        cited_urls=_cited_urls(ai_overview),
        raw=raw,
    )


class SerpApiAIOProvider:
    key = "google_aio"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.serpapi_api_key
        self._default_location = settings.serpapi_default_location

    def run(self, prompt: str, opts: dict[str, Any] | None = None) -> EngineResult:
        import httpx

        opts = opts or {}
        params = {
            "engine": "google",
            "q": prompt,
            "api_key": self._api_key,
            "location": opts.get("location") or self._default_location,
            "hl": opts.get("language") or "en",
        }
        with httpx.Client(timeout=30) as client:
            resp = client.get(SERPAPI_URL, params=params)
            resp.raise_for_status()
            raw = resp.json()

        ai_overview = raw.get("ai_overview") or {}
        # AI Overview sometimes returns only a page_token; fetch the block itself.
        if ai_overview.get("page_token") and not ai_overview.get("text_blocks"):
            with httpx.Client(timeout=30) as client:
                r2 = client.get(
                    SERPAPI_URL,
                    params={
                        "engine": "google_ai_overview",
                        "page_token": ai_overview["page_token"],
                        "api_key": self._api_key,
                    },
                )
                r2.raise_for_status()
                follow = r2.json()
            if follow.get("ai_overview"):
                raw["ai_overview"] = follow["ai_overview"]

        result = extract_aio_result(raw)
        log_event(
            log,
            "provider.google_aio.run",
            prompt_preview=prompt[:120],
            aio_present=bool(raw.get("ai_overview")),
            answer_len=len(result.answer_text),
            citations=len(result.cited_urls),
        )
        return result
