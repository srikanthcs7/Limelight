"""Prompt edit/delete endpoints used by the review modal."""
from __future__ import annotations

import app.api.deps as deps
import app.llm as llm_mod
from app.config import Settings
from app.db import get_db
from app.main import app
from app.models import Prompt
from app.seed import seed_getquizsolve
from fastapi.testclient import TestClient


def _client(db, monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(admin_token="secret"))

    def _dep():
        yield db

    app.dependency_overrides[get_db] = _dep
    return TestClient(app)


def test_edit_and_delete_prompt(db, monkeypatch):
    brand = seed_getquizsolve(db)
    pid = str(db.query(Prompt).filter(Prompt.brand_id == brand.id).first().id)
    client = _client(db, monkeypatch)
    h = {"X-Admin-Token": "secret"}
    try:
        # edit text
        r = client.patch(f"/brands/{brand.id}/prompts/{pid}", json={"text": "edited prompt"}, headers=h)
        assert r.status_code == 200 and r.json()["text"] == "edited prompt"

        # delete (no runs) -> hard delete
        r = client.delete(f"/brands/{brand.id}/prompts/{pid}", headers=h)
        assert r.status_code == 200 and r.json()["deleted"] is True
        assert db.query(Prompt).filter(Prompt.id == pid).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_edit_requires_token(db, monkeypatch):
    brand = seed_getquizsolve(db)
    pid = str(db.query(Prompt).filter(Prompt.brand_id == brand.id).first().id)
    client = _client(db, monkeypatch)
    try:
        assert client.patch(f"/brands/{brand.id}/prompts/{pid}", json={"text": "x"}).status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_bulk_delete(db, monkeypatch):
    brand = seed_getquizsolve(db)
    pid = str(db.query(Prompt).filter(Prompt.brand_id == brand.id).first().id)
    client = _client(db, monkeypatch)
    try:
        r = client.post(
            f"/brands/{brand.id}/prompts:bulk-delete",
            json={"prompt_ids": [pid]},
            headers={"X-Admin-Token": "secret"},
        )
        assert r.status_code == 200 and r.json()["deleted"] == 1
        assert db.query(Prompt).filter(Prompt.id == pid).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_refine_selected(db, monkeypatch):
    brand = seed_getquizsolve(db)
    pid = str(db.query(Prompt).filter(Prompt.brand_id == brand.id).first().id)
    monkeypatch.setattr(
        llm_mod, "complete_json", lambda s, u, model=None: {"items": [{"i": 0, "text": "a sharper prompt"}]}
    )
    client = _client(db, monkeypatch)
    try:
        r = client.post(
            f"/brands/{brand.id}/prompts:refine",
            json={"prompt_ids": [pid]},
            headers={"X-Admin-Token": "secret"},
        )
        assert r.status_code == 200 and r.json()["refined"] == 1
        assert db.get(Prompt, __import__("uuid").UUID(pid)).text == "a sharper prompt"
    finally:
        app.dependency_overrides.clear()
