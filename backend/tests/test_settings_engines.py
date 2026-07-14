import app.api.deps as deps
import app.pipeline.runner as runner_mod
import app.llm as llm_mod
from app.config import Settings
from app.db import get_db
from app.main import app
from app.models import Engine, Run
from app.pipeline.runner import run_brand_all_engines
from app.providers.base import EngineResult
from app.providers.openai_provider import extract_engine_result
from app.providers.serpapi_provider import extract_aio_result
from app.seed import seed_getquizsolve
from fastapi.testclient import TestClient
from tests.fixtures import RESPONSES_WEB_SEARCH_DUMP, SERPAPI_AIO_RESPONSE

FAKE_EXTRACTION = {"mentions": [{"name": "GetQuizSolve", "position": 1, "sentiment": "positive"}]}


def _client(db, monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(admin_token="secret"))

    def _dep():
        yield db

    app.dependency_overrides[get_db] = _dep
    return TestClient(app)


def test_update_settings(db, monkeypatch):
    brand = seed_getquizsolve(db)
    client = _client(db, monkeypatch)
    try:
        r = client.patch(
            f"/brands/{brand.id}/settings",
            json={"tracked_engines": ["openai", "google_aio"], "run_frequency": "hourly", "location": "India"},
            headers={"X-Admin-Token": "secret"},
        )
        assert r.status_code == 200
        body = r.json()
        assert set(body["tracked_engines"]) == {"openai", "google_aio"}
        assert body["run_frequency"] == "hourly"
        assert body["location"] == "India"
    finally:
        app.dependency_overrides.clear()


def test_update_settings_rejects_unknown_engine(db, monkeypatch):
    brand = seed_getquizsolve(db)
    client = _client(db, monkeypatch)
    try:
        r = client.patch(
            f"/brands/{brand.id}/settings",
            json={"tracked_engines": ["not_a_real_engine"]},
            headers={"X-Admin-Token": "secret"},
        )
        assert r.status_code == 400
    finally:
        app.dependency_overrides.clear()


class _OpenAIFake:
    key = "openai"

    def run(self, prompt, opts=None) -> EngineResult:
        return extract_engine_result(RESPONSES_WEB_SEARCH_DUMP)


class _AIOFake:
    key = "google_aio"

    def run(self, prompt, opts=None) -> EngineResult:
        assert opts and "location" in opts  # per-brand opts are passed through
        return extract_aio_result(SERPAPI_AIO_RESPONSE)


def test_run_all_engines_stores_runs_per_engine(db, monkeypatch):
    brand = seed_getquizsolve(db)
    brand.tracked_engines = ["openai", "google_aio"]
    brand.location = "United States"
    db.flush()
    # make sure the google_aio engine row exists
    if not db.query(Engine).filter(Engine.key == "google_aio").first():
        db.add(Engine(key="google_aio"))
        db.flush()

    providers = {"openai": _OpenAIFake(), "google_aio": _AIOFake()}
    monkeypatch.setattr(runner_mod, "get_provider", lambda key: providers[key])
    monkeypatch.setattr(llm_mod, "complete_json", lambda s, u, model=None: FAKE_EXTRACTION)

    result = run_brand_all_engines(db, brand.id)
    assert result == {"openai": 1, "google_aio": 1}
    assert db.query(Run).count() == 2  # one run per engine for the single prompt


def test_engine_row_self_heals(db, monkeypatch):
    """Enabling an engine that was never seeded should still run (row auto-created)."""
    brand = seed_getquizsolve(db)
    brand.tracked_engines = ["google_aio"]
    db.query(Engine).filter(Engine.key == "google_aio").delete()  # simulate un-seeded engine
    db.flush()

    monkeypatch.setattr(runner_mod, "get_provider", lambda key: _AIOFake())
    monkeypatch.setattr(llm_mod, "complete_json", lambda s, u, model=None: FAKE_EXTRACTION)

    result = run_brand_all_engines(db, brand.id)
    assert result == {"google_aio": 1}
    assert db.query(Engine).filter(Engine.key == "google_aio").count() == 1  # recreated
