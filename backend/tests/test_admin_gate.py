"""The write endpoints must be gated by the admin token."""
from __future__ import annotations

import app.api.deps as deps
from app.config import Settings
from app.db import get_db
from app.main import app
from fastapi.testclient import TestClient


def _override_db(db):
    def _dep():
        yield db

    return _dep


def test_seed_requires_token_configured(db, monkeypatch):
    # ADMIN_TOKEN unset -> writes disabled (503).
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(admin_token=""))
    app.dependency_overrides[get_db] = _override_db(db)
    try:
        client = TestClient(app)
        assert client.post("/admin/seed").status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_seed_rejects_wrong_token(db, monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(admin_token="secret"))
    app.dependency_overrides[get_db] = _override_db(db)
    try:
        client = TestClient(app)
        assert client.post("/admin/seed", headers={"X-Admin-Token": "nope"}).status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_seed_accepts_correct_token(db, monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(admin_token="secret"))
    app.dependency_overrides[get_db] = _override_db(db)
    try:
        client = TestClient(app)
        resp = client.post("/admin/seed", headers={"X-Admin-Token": "secret"})
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "GetQuizSolve"
    finally:
        app.dependency_overrides.clear()
