"""Shared OpenAI intel-model helper (prompt generation, entity extraction, gap
recommendations). One place to call the model in JSON mode — and one place for
tests to monkeypatch."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings
from app.logging_config import log_event

log = logging.getLogger("limelight.llm")


def complete_json(system: str, user: str, model: str | None = None) -> dict[str, Any]:
    """Call the intel model in JSON mode and parse the object. Raises on failure
    (callers decide whether to fall back)."""
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=model or settings.openai_intel_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        log_event(log, "llm.bad_json", level=logging.WARNING, preview=content[:200])
        raise
