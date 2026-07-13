import app.pipeline.prompt_gen as pg
from app.models import Competitor, Prompt
from app.pipeline.prompt_gen import _validate, generate_for_brand
from app.seed import seed_getquizsolve

FAKE_LLM = {
    "category": "AI study-helper Chrome extensions for LMS platforms",
    "competitors": [
        {"name": "CheatMate", "aliases": [], "domain": None},  # already seeded -> dedup
        {"name": "StudyFetch", "aliases": ["Study Fetch"], "domain": "studyfetch.com"},  # new
    ],
    "prompts": [
        {"text": "best AI homework helper for Pearson MyLab", "intent_type": "best_of"},
        {"text": "Coursology alternatives for students", "intent_type": "alternatives"},
        {"text": "GetQuizSolve vs Coursology", "intent_type": "comparison"},
        {"text": "how to get help on McGraw-Hill Connect quizzes", "intent_type": "problem_first"},
        {"text": "best AI homework helper for Pearson MyLab", "intent_type": "best_of"},  # dup text
        {"text": "", "intent_type": "best_of"},  # empty -> dropped
        {"text": "bad intent", "intent_type": "nonsense"},  # bad intent -> dropped
    ],
}


def test_validate_filters_dupes_and_bad_rows():
    result = _validate(FAKE_LLM)
    texts = [p.text for p in result.prompts]
    assert len(texts) == 4  # dedup + drop empty + drop bad intent
    assert all(p.intent_type in pg.INTENT_TYPES for p in result.prompts)
    assert {c["name"] for c in result.competitors} == {"CheatMate", "StudyFetch"}


def test_generate_for_brand_persists(db, monkeypatch):
    monkeypatch.setattr(pg, "scrape_site", lambda domain, max_chars=6000: "site text about study tools")
    monkeypatch.setattr(pg, "_complete_json", lambda system, user: FAKE_LLM)

    brand = seed_getquizsolve(db)
    before = db.query(Prompt).filter(Prompt.brand_id == brand.id).count()

    summary = generate_for_brand(db, brand.id)

    assert summary["added_prompts"] == 4
    assert summary["added_competitors"] == 1  # StudyFetch new; CheatMate deduped
    after = db.query(Prompt).filter(Prompt.brand_id == brand.id).count()
    assert after == before + 4
    assert db.query(Competitor).filter(Competitor.name == "StudyFetch").count() == 1


def test_generate_is_idempotent_on_prompt_text(db, monkeypatch):
    monkeypatch.setattr(pg, "scrape_site", lambda domain, max_chars=6000: "x")
    monkeypatch.setattr(pg, "_complete_json", lambda system, user: FAKE_LLM)
    brand = seed_getquizsolve(db)

    generate_for_brand(db, brand.id)
    second = generate_for_brand(db, brand.id)
    assert second["added_prompts"] == 0  # same texts -> nothing new
