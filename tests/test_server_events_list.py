"""GET /v1/events/ — list events (used by openclaw plugin's listEvents).

Mirrors the per-event polling shape of GET /v1/event/{id}/ but returns a
``{"results": [...]}`` envelope and supports filtering by status / user_id
plus a hard ``limit`` cap. Newest events come first.
"""

from __future__ import annotations

import importlib
import os
import sys
import time as _t
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")
pytest.importorskip("alembic", reason="alembic not installed")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO_ROOT / "server"


@pytest.fixture
def sqlite_db(tmp_path):
    """Spin up a fresh SQLite DB at ``tmp_path/test.db`` and bring it to head."""
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"

    sys.path.insert(0, str(SERVER_DIR))
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(SERVER_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(SERVER_DIR / "alembic"))
        cfg.set_main_option("sqlalchemy.url", url)

        with patch.dict(os.environ, {"POSTGRES_HOST": "ignored"}):
            command.upgrade(cfg, "head")
    finally:
        sys.path.remove(str(SERVER_DIR))

    engine = create_engine(url)
    yield url, engine
    engine.dispose()


@pytest.fixture
def client(sqlite_db):
    """Build a TestClient backed by a SQLite DB and a mocked Memory."""
    url, engine = sqlite_db
    sys.path.insert(0, str(SERVER_DIR))

    fake_memory = MagicMock()
    fake_memory.search.return_value = [{"id": "mem-1", "memory": "x", "score": 0.9}]
    fake_memory.add.return_value = {"results": []}

    SessionLocalSqlite = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    env_patches = {
        "OPENAI_API_KEY": "fake-key",
        "ADMIN_API_KEY": "",
        "AUTH_DISABLED": "true",
        "JWT_SECRET": "test-secret-test-secret-test-secret",
    }
    try:
        with patch.dict(os.environ, env_patches, clear=False):
            import db as server_db

            server_db.engine = engine
            server_db.SessionLocal = SessionLocalSqlite

            with patch("mem0.Memory.from_config", return_value=fake_memory):
                import main as server_main

                importlib.reload(server_main)
                server_main.set_session_factory(SessionLocalSqlite)
                server_main.initialize_state(server_main.DEFAULT_CONFIG)
                yield TestClient(server_main.app), fake_memory, SessionLocalSqlite
    finally:
        sys.path.remove(str(SERVER_DIR))


def _create_event(session_factory, status, payload=None, result=None, error=None):
    """Insert an event row directly via the ORM and return its UUID string."""
    sys.path.insert(0, str(SERVER_DIR))
    try:
        from models import Event

        with session_factory() as s:
            ev = Event(status=status, payload=payload or {}, result=result, error=error)
            s.add(ev)
            s.commit()
            s.refresh(ev)
            return str(ev.id)
    finally:
        sys.path.remove(str(SERVER_DIR))


class TestEventsList:
    def test_returns_envelope_with_results_key(self, client):
        c, _, SessionLocal = client
        _create_event(SessionLocal, "SUCCEEDED", payload={"user_id": "alice"})
        resp = c.get("/v1/events/")
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert isinstance(body["results"], list)

    def test_each_item_has_v1_event_shape(self, client):
        c, _, SessionLocal = client
        _create_event(
            SessionLocal,
            "SUCCEEDED",
            payload={"user_id": "alice"},
            result={"results": []},
        )
        resp = c.get("/v1/events/")
        item = resp.json()["results"][0]
        assert set(item.keys()) >= {
            "event_id",
            "status",
            "result",
            "error",
            "created_at",
            "updated_at",
        }

    def test_filters_by_status(self, client):
        c, _, SessionLocal = client
        _create_event(SessionLocal, "PENDING", payload={"user_id": "alice"})
        _create_event(SessionLocal, "SUCCEEDED", payload={"user_id": "alice"})
        _create_event(SessionLocal, "FAILED", payload={"user_id": "alice"}, error="boom")
        resp = c.get("/v1/events/?status=FAILED")
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["status"] == "FAILED"
        assert results[0]["error"] == "boom"

    def test_filters_by_user_id(self, client):
        c, _, SessionLocal = client
        _create_event(SessionLocal, "SUCCEEDED", payload={"user_id": "alice"})
        _create_event(SessionLocal, "SUCCEEDED", payload={"user_id": "bob"})
        resp = c.get("/v1/events/?user_id=alice")
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["status"] == "SUCCEEDED"

    def test_limit_caps_count(self, client):
        c, _, SessionLocal = client
        for _ in range(5):
            _create_event(SessionLocal, "SUCCEEDED", payload={"user_id": "alice"})
        resp = c.get("/v1/events/?limit=2")
        assert len(resp.json()["results"]) == 2

    def test_order_is_created_at_desc(self, client):
        c, _, SessionLocal = client
        first_id = _create_event(SessionLocal, "SUCCEEDED", payload={"user_id": "alice"})
        # Ensure timestamps differ (sqlite resolution can collapse if too fast)
        _t.sleep(0.01)
        second_id = _create_event(SessionLocal, "SUCCEEDED", payload={"user_id": "alice"})
        results = c.get("/v1/events/").json()["results"]
        assert results[0]["event_id"] == second_id
        assert results[1]["event_id"] == first_id

    def test_limit_bounds(self, client):
        c, _, _ = client
        assert c.get("/v1/events/?limit=0").status_code == 422
        assert c.get("/v1/events/?limit=201").status_code == 422

    def test_invalid_status_rejected(self, client):
        c, _, _ = client
        resp = c.get("/v1/events/?status=BOGUS")
        assert resp.status_code == 422
