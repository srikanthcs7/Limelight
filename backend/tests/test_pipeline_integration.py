"""End-to-end proof of the M1 pipeline with a mocked provider (no live API):
seed -> runner -> detection -> citations -> storage -> scoring.
"""
from __future__ import annotations

import app.llm as llm_mod
import app.pipeline.runner as runner_mod
from app.models import Citation, Mention, Run
from app.pipeline.runner import run_brand_prompts
from app.pipeline.scoring import recompute_scores
from app.providers.base import EngineResult
from app.providers.openai_provider import extract_engine_result
from app.seed import seed_getquizsolve
from tests.fixtures import RESPONSES_WEB_SEARCH_DUMP

# What the mocked LLM extraction returns for the fixture answer.
FAKE_EXTRACTION = {
    "mentions": [
        {"name": "GetQuizSolve", "position": 1, "sentiment": "positive"},
        {"name": "Coursology", "position": 2, "sentiment": "neutral"},
        {"name": "QuizAce", "position": 3, "sentiment": "neutral"},
        {"name": "CheatMate", "position": 4, "sentiment": "neutral"},
    ]
}


class _FakeProvider:
    key = "openai"

    def run(self, prompt, opts=None) -> EngineResult:
        # Reuse the real extractor so we exercise the true parsing path.
        return extract_engine_result(RESPONSES_WEB_SEARCH_DUMP)


def test_full_pipeline(db, monkeypatch):
    monkeypatch.setattr(runner_mod, "get_provider", lambda key: _FakeProvider())
    monkeypatch.setattr(llm_mod, "complete_json", lambda system, user, model=None: FAKE_EXTRACTION)

    brand = seed_getquizsolve(db)
    runs = run_brand_prompts(db, brand.id)
    assert len(runs) == 1
    run = runs[0]

    # Run persisted, immutable payload captured.
    assert db.get(Run, run.id) is not None
    assert "GetQuizSolve" in run.answer_text
    assert run.raw_response_json["id"] == "resp_abc123"

    # Mentions: brand + the 3 competitors that appear, brand first.
    mentions = db.query(Mention).filter(Mention.run_id == run.id).all()
    names = {m.entity_name for m in mentions}
    assert "GetQuizSolve" in names
    assert {"Coursology", "QuizAce", "CheatMate"}.issubset(names)
    brand_m = next(m for m in mentions if m.is_tracked_brand)
    assert brand_m.position == 1

    # Citations deduped: reddit once, getquizsolve once.
    citations = db.query(Citation).filter(Citation.run_id == run.id).all()
    domains = sorted(c.domain for c in citations)
    assert domains == ["getquizsolve.com", "reddit.com"]

    # brand mention carries sentiment from the LLM pass.
    assert brand_m.sentiment == "positive"

    # Scoring over the run (all-time window): brand present + first + self-cited.
    result = recompute_scores(db, brand.id)["all"]
    assert result["total_runs"] == 1
    assert result["mention_rate"] == 1.0
    assert result["citation_rate"] == 1.0
    assert 0.0 < result["share_of_voice"] <= 1.0
    assert result["visibility_score"] > 0


def test_runs_are_append_only(db, monkeypatch):
    monkeypatch.setattr(runner_mod, "get_provider", lambda key: _FakeProvider())
    brand = seed_getquizsolve(db)

    run_brand_prompts(db, brand.id)
    run_brand_prompts(db, brand.id)  # a second run of the same prompt

    total = db.query(Run).count()
    assert total == 2  # appended, not overwritten


def test_scores_upsert_same_day(db, monkeypatch):
    from app.models import Score

    monkeypatch.setattr(runner_mod, "get_provider", lambda key: _FakeProvider())
    monkeypatch.setattr(llm_mod, "complete_json", lambda system, user, model=None: FAKE_EXTRACTION)
    brand = seed_getquizsolve(db)
    run_brand_prompts(db, brand.id)

    recompute_scores(db, brand.id)
    recompute_scores(db, brand.id)  # same day -> upserts each of the 3 windows

    # 3 standard windows (all / 30d / 7d), upserted not duplicated.
    assert db.query(Score).filter(Score.brand_id == brand.id).count() == 3
