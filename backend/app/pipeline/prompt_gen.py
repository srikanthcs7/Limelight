"""Prompt generation (M2).

Given a brand's domain: scrape the site, infer its category + competitors, and
generate 40-100 realistic buyer prompts across intent types. An LLM job (OpenAI
intel model).

The network steps (scrape, LLM) are isolated behind small functions so the
persistence + validation logic is unit-testable with fixtures.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx
import trafilatura
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import log_event
from app.models import Brand, Competitor, Prompt

log = logging.getLogger("limelight.prompt_gen")

INTENT_TYPES = {"best_of", "comparison", "alternatives", "problem_first"}
DEFAULT_TARGET = 60  # middle of the 40-100 range


@dataclass
class GeneratedPrompt:
    text: str
    intent_type: str


@dataclass
class PromptGenResult:
    category: str | None
    competitors: list[dict]  # {name, aliases[], domain?}
    prompts: list[GeneratedPrompt] = field(default_factory=list)


# --- network steps (mocked in tests) -------------------------------------------------

def scrape_site(domain: str, max_chars: int = 6000) -> str:
    """Fetch the homepage and extract its main text. Returns "" on failure."""
    url = domain if domain.startswith("http") else f"https://{domain}"
    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": "LimelightBot/0.1 (+https://limelight-geo.fly.dev)"},
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        log_event(log, "prompt_gen.scrape_failed", level=logging.WARNING, domain=domain, error=str(exc))
        return ""
    text = trafilatura.extract(resp.text) or ""
    return text[:max_chars]


def _complete_json(system: str, user: str) -> dict:
    """Call the OpenAI intel model in JSON mode and parse the object."""
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.openai_intel_model,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return json.loads(resp.choices[0].message.content or "{}")


# --- pure logic ----------------------------------------------------------------------

_SYSTEM = (
    "You are a market researcher for AI-search visibility (GEO/AEO). Given a "
    "brand's website text, infer its product category and real competitors, then "
    "write realistic buyer prompts a person would type into an AI assistant when "
    "researching this category. Return STRICT JSON only."
)


def _build_user_prompt(brand: Brand, site_text: str, known_competitors: list[str], target: int) -> str:
    return (
        f"Brand: {brand.display_name} ({brand.domain})\n"
        f"Known competitors (extend, don't just repeat): {', '.join(known_competitors) or 'none'}\n\n"
        f"Website text:\n{site_text or '(no site text available; infer from the brand name/domain)'}\n\n"
        f"Return JSON with this exact shape:\n"
        '{\n'
        '  "category": "short category description",\n'
        '  "competitors": [{"name": "...", "aliases": ["..."], "domain": "... or null"}],\n'
        '  "prompts": [{"text": "buyer question", "intent_type": "best_of|comparison|alternatives|problem_first"}]\n'
        "}\n\n"
        f"Generate {target} prompts, spread across all four intent_type values "
        "(best_of, comparison, alternatives, problem_first). Prompts must sound "
        "like real buyers, mention the category/use-cases (and competitors for "
        "comparison/alternatives intents), and must NOT all name the brand."
    )


def _validate(raw: dict) -> PromptGenResult:
    prompts: list[GeneratedPrompt] = []
    seen: set[str] = set()
    for p in raw.get("prompts", []) or []:
        text = (p.get("text") or "").strip()
        intent = (p.get("intent_type") or "").strip()
        if not text or intent not in INTENT_TYPES:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        prompts.append(GeneratedPrompt(text=text, intent_type=intent))

    competitors = []
    for c in raw.get("competitors", []) or []:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        competitors.append(
            {
                "name": name,
                "aliases": [a for a in (c.get("aliases") or []) if isinstance(a, str)],
                "domain": (c.get("domain") or None),
            }
        )

    category = (raw.get("category") or "").strip() or None
    return PromptGenResult(category=category, competitors=competitors, prompts=prompts)


def generate_prompt_set(
    brand: Brand, site_text: str, known_competitors: list[str], target: int = DEFAULT_TARGET
) -> PromptGenResult:
    raw = _complete_json(_SYSTEM, _build_user_prompt(brand, site_text, known_competitors, target))
    return _validate(raw)


def persist_generated(
    db: Session, brand: Brand, result: PromptGenResult, deactivate_existing: bool = False
) -> dict:
    """Persist generated prompts + newly discovered competitors. Idempotent on
    prompt text (skips duplicates). Sets the brand category if it was empty."""
    if result.category and not brand.category:
        brand.category = result.category

    existing_comp = {c.name.lower() for c in db.scalars(select(Competitor).where(Competitor.brand_id == brand.id))}
    added_competitors = 0
    for c in result.competitors:
        if c["name"].lower() in existing_comp:
            continue
        db.add(Competitor(brand_id=brand.id, name=c["name"], aliases=c["aliases"], domain=c["domain"]))
        existing_comp.add(c["name"].lower())
        added_competitors += 1

    if deactivate_existing:
        for p in db.scalars(select(Prompt).where(Prompt.brand_id == brand.id)):
            p.active = False

    existing_texts = {
        t.lower() for t in db.scalars(select(Prompt.text).where(Prompt.brand_id == brand.id))
    }
    added_prompts = 0
    for gp in result.prompts:
        if gp.text.lower() in existing_texts:
            continue
        db.add(Prompt(brand_id=brand.id, text=gp.text, intent_type=gp.intent_type, active=True))
        existing_texts.add(gp.text.lower())
        added_prompts += 1

    db.flush()
    summary = {
        "brand": brand.display_name,
        "added_prompts": added_prompts,
        "added_competitors": added_competitors,
        "category": brand.category,
    }
    log_event(log, "prompt_gen.persisted", **summary)
    return summary


def generate_for_brand(db: Session, brand_id, target: int = DEFAULT_TARGET) -> dict:
    """Orchestrate: scrape → LLM generate → persist."""
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise ValueError(f"brand {brand_id} not found")
    known = [c.name for c in db.scalars(select(Competitor).where(Competitor.brand_id == brand.id))]
    site_text = scrape_site(brand.domain)
    result = generate_prompt_set(brand, site_text, known, target)
    return persist_generated(db, brand, result)
