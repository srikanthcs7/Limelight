import app.llm as llm_mod
import app.pipeline.runner as runner_mod
from app.pipeline.analytics import (
    intent_coverage,
    prompt_breakdown,
    share_of_voice,
    sov_timeline,
    top_sources,
)
from app.pipeline.runner import run_brand_prompts
from app.providers.base import EngineResult
from app.providers.openai_provider import extract_engine_result
from app.seed import seed_getquizsolve
from tests.fixtures import RESPONSES_WEB_SEARCH_DUMP

FAKE_EXTRACTION = {
    "mentions": [
        {"name": "GetQuizSolve", "position": 1, "sentiment": "positive"},
        {"name": "Coursology", "position": 2, "sentiment": "neutral"},
        {"name": "QuizAce", "position": 3, "sentiment": "neutral"},
        {"name": "CheatMate", "position": 4, "sentiment": "neutral"},
    ]
}


class _Fake:
    key = "openai"

    def run(self, prompt, opts=None) -> EngineResult:
        return extract_engine_result(RESPONSES_WEB_SEARCH_DUMP)


def _seed_and_run(db, monkeypatch):
    monkeypatch.setattr(runner_mod, "get_provider", lambda key: _Fake())
    monkeypatch.setattr(llm_mod, "complete_json", lambda s, u, model=None: FAKE_EXTRACTION)
    brand = seed_getquizsolve(db)
    run_brand_prompts(db, brand.id)
    return brand


def test_share_of_voice(db, monkeypatch):
    brand = _seed_and_run(db, monkeypatch)
    sov = share_of_voice(db, brand.id)
    names = {r["entity_name"]: r for r in sov}
    assert names["GetQuizSolve"]["is_tracked_brand"] is True
    assert abs(sum(r["share"] for r in sov) - 1.0) < 0.01
    assert names["GetQuizSolve"]["mentions"] == 1


def test_top_sources(db, monkeypatch):
    brand = _seed_and_run(db, monkeypatch)
    sources = top_sources(db, brand.id)
    domains = {s["domain"]: s["citations"] for s in sources}
    assert domains.get("reddit.com") == 1  # deduped in the run
    assert "getquizsolve.com" in domains


def test_prompt_breakdown(db, monkeypatch):
    brand = _seed_and_run(db, monkeypatch)
    rows = prompt_breakdown(db, brand.id)
    assert len(rows) == 1
    assert rows[0]["brand_mentioned"] is True
    assert rows[0]["position"] == 1
    assert rows[0]["runs_count"] == 1


def test_share_of_voice_sentiment(db, monkeypatch):
    brand = _seed_and_run(db, monkeypatch)
    sov = {r["entity_name"]: r for r in share_of_voice(db, brand.id)}
    assert sov["GetQuizSolve"]["positive"] == 1  # tagged positive
    assert sov["QuizAce"]["neutral"] == 1  # tagged neutral


def test_intent_coverage(db, monkeypatch):
    brand = _seed_and_run(db, monkeypatch)
    cov = intent_coverage(db, brand.id)
    # seeded prompt is best_of and the brand is mentioned -> coverage 1.0
    best = next(c for c in cov if c["intent_type"] == "best_of")
    assert best["total"] == 1 and best["mentioned"] == 1 and best["coverage"] == 1.0


def test_sov_timeline(db, monkeypatch):
    brand = _seed_and_run(db, monkeypatch)
    tl = sov_timeline(db, brand.id)
    assert len(tl["days"]) == 1
    names = {s["name"] for s in tl["series"]}
    assert "GetQuizSolve" in names
    brand_series = next(s for s in tl["series"] if s["name"] == "GetQuizSolve")
    assert brand_series["is_tracked_brand"] is True
    assert len(brand_series["points"]) == 1
