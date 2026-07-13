"""Seed data for the dogfood target (GetQuizSolve) and the OpenAI engine row."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brand, Competitor, Engine, Prompt
from app.providers.registry import provider_keys

# spec §2 — dogfood target.
GETQUIZSOLVE = {
    "domain": "getquizsolve.com",
    "display_name": "GetQuizSolve",
    "aliases": ["Get Quiz Solve", "QuizSolve"],
    "category": "AI study-helper Chrome extension for LMS platforms",
    "competitors": [
        {"name": "CheatMate", "aliases": [], "domain": None},
        {"name": "QuizSolverAI", "aliases": ["Quiz Solver AI"], "domain": None},
        {"name": "QuizAce", "aliases": ["Quiz Ace"], "domain": None},
        {"name": "Coursology", "aliases": [], "domain": None},
    ],
    # One hand-written prompt for M0/M1; M2 generates the full 40–100 set.
    "prompts": [
        {
            "text": "best AI study helper Chrome extension for online courses",
            "intent_type": "best_of",
        },
    ],
}


def ensure_engines(db: Session) -> None:
    """Insert an `engines` row for every registered provider key."""
    existing = set(db.scalars(select(Engine.key)))
    for key in provider_keys():
        if key not in existing:
            db.add(Engine(key=key))
    db.flush()


def seed_getquizsolve(db: Session) -> Brand:
    """Idempotent: creates the brand only if its domain isn't present yet."""
    ensure_engines(db)

    brand = db.scalar(select(Brand).where(Brand.domain == GETQUIZSOLVE["domain"]))
    if brand is not None:
        return brand

    brand = Brand(
        domain=GETQUIZSOLVE["domain"],
        display_name=GETQUIZSOLVE["display_name"],
        aliases=GETQUIZSOLVE["aliases"],
        category=GETQUIZSOLVE["category"],
    )
    db.add(brand)
    db.flush()

    for c in GETQUIZSOLVE["competitors"]:
        db.add(Competitor(brand_id=brand.id, name=c["name"], aliases=c["aliases"], domain=c["domain"]))
    for p in GETQUIZSOLVE["prompts"]:
        db.add(Prompt(brand_id=brand.id, text=p["text"], intent_type=p["intent_type"]))

    db.flush()
    return brand
