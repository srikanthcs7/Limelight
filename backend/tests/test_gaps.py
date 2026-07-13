import app.llm as llm_mod
import app.pipeline.runner as runner_mod
from app.pipeline.gaps import compute_gaps, recommend
from app.pipeline.runner import run_brand_prompts
from app.providers.base import EngineResult
from app.providers.openai_provider import extract_engine_result
from app.seed import seed_getquizsolve
from tests.fixtures import RESPONSES_WEB_SEARCH_DUMP

# Extraction where the tracked brand is ABSENT but competitors appear.
COMPETITORS_ONLY = {
    "mentions": [
        {"name": "Coursology", "position": 1, "sentiment": "neutral"},
        {"name": "CheatMate", "position": 2, "sentiment": "neutral"},
    ]
}


class _Fake:
    key = "openai"

    def run(self, prompt, opts=None) -> EngineResult:
        return extract_engine_result(RESPONSES_WEB_SEARCH_DUMP)


def test_prompt_gaps_flags_absent_brand(db, monkeypatch):
    monkeypatch.setattr(runner_mod, "get_provider", lambda key: _Fake())
    monkeypatch.setattr(llm_mod, "complete_json", lambda s, u, model=None: COMPETITORS_ONLY)
    brand = seed_getquizsolve(db)
    run_brand_prompts(db, brand.id)

    gaps = compute_gaps(db, brand.id)
    assert len(gaps["prompt_gaps"]) == 1
    g = gaps["prompt_gaps"][0]
    assert g["brand_mentioned"] is False
    assert set(g["competitors_present"]) >= {"Coursology", "CheatMate"}
    # citations still captured -> source gaps present
    assert {s["domain"] for s in gaps["source_gaps"]} >= {"reddit.com", "getquizsolve.com"}


def test_recommend_uses_llm(db, monkeypatch):
    monkeypatch.setattr(runner_mod, "get_provider", lambda key: _Fake())
    monkeypatch.setattr(llm_mod, "complete_json", lambda s, u, model=None: COMPETITORS_ONLY)
    brand = seed_getquizsolve(db)
    run_brand_prompts(db, brand.id)

    monkeypatch.setattr(
        llm_mod,
        "complete_json",
        lambda s, u, model=None: {"recommendations": ["Publish a comparison page", "Answer on Reddit"]},
    )
    recs = recommend(db, brand.id)
    assert recs == ["Publish a comparison page", "Answer on Reddit"]
