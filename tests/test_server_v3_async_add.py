"""E2E tests for ``POST /v3/memories/add/`` — async via BackgroundTasks.

The new V3 add route returns an ``event_id`` immediately and runs the actual
extraction in a FastAPI background task. ``TestClient`` runs the background
task synchronously after the response is sent, so we can poll the events
table without sleeping.
"""

from __future__ import annotations

import importlib
import os
import sys
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

    # Make sure server/ is on sys.path so alembic env.py imports work
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
    """Build a TestClient backed by a SQLite DB and a mocked Memory.

    Steps:
      1. Patch ``db.engine`` and ``db.SessionLocal`` so the running server uses
         our SQLite file (FastAPI/SQLAlchemy share the connection pool).
      2. Patch ``Memory.from_config`` to a mock so we don't need a real LLM.
      3. Reload ``server.main`` so it re-runs ``initialize_state`` against the
         fresh DB (which has the seeded default project row).
    """
    url, engine = sqlite_db
    sys.path.insert(0, str(SERVER_DIR))

    fake_memory = MagicMock()
    fake_memory.search.return_value = [{"id": "mem-1", "memory": "x", "score": 0.9}]
    # Default add() return must match what the V3 worker persists into Event.result.
    fake_memory.add.return_value = {"results": [{"id": "mem-1", "event": "ADD", "memory": "x"}]}

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
                # set_session_factory was called inside reload via initialize_state,
                # but server_state imported the *old* SessionLocal — refresh it.
                server_main.set_session_factory(SessionLocalSqlite)
                server_main.initialize_state(server_main.DEFAULT_CONFIG)
                yield TestClient(server_main.app), fake_memory, SessionLocalSqlite
    finally:
        sys.path.remove(str(SERVER_DIR))


class TestV3Add:
    def test_returns_event_id_with_pending_status(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I love jazz"}],
            "user_id": "alice",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in {"PENDING", "SUCCEEDED"}  # TestClient runs bg sync
        assert "event_id" in body and body["event_id"]

    def test_missing_entity_id_returns_400(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I love jazz"}],
        })
        assert resp.status_code == 400

    def test_background_task_persists_succeeded_event(self, client):
        c, _, SessionLocal = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I love jazz"}],
            "user_id": "alice",
        })
        event_id = resp.json()["event_id"]

        sys.path.insert(0, str(SERVER_DIR))
        try:
            from models import Event
            with SessionLocal() as s:
                import uuid as _uuid
                ev = s.get(Event, _uuid.UUID(event_id))
                assert ev is not None
                assert ev.status == "SUCCEEDED"
                assert ev.result == {"results": [{"id": "mem-1", "event": "ADD", "memory": "x"}]}
                assert ev.error is None
        finally:
            sys.path.remove(str(SERVER_DIR))

    def test_failure_marks_event_failed_with_error(self, client):
        c, fake_memory, SessionLocal = client
        fake_memory.add.side_effect = RuntimeError("LLM exploded")

        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I love jazz"}],
            "user_id": "alice",
        })
        event_id = resp.json()["event_id"]

        sys.path.insert(0, str(SERVER_DIR))
        try:
            from models import Event
            with SessionLocal() as s:
                import uuid as _uuid
                ev = s.get(Event, _uuid.UUID(event_id))
                assert ev.status == "FAILED"
                assert "LLM exploded" in (ev.error or "")
        finally:
            sys.path.remove(str(SERVER_DIR))


class TestEventPoll:
    def test_poll_returns_event_state(self, client):
        c, _, _ = client
        post = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "x"}],
            "user_id": "alice",
        })
        event_id = post.json()["event_id"]

        resp = c.get(f"/v1/event/{event_id}/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == event_id
        assert body["status"] == "SUCCEEDED"
        assert body["result"] == {"results": [{"id": "mem-1", "event": "ADD", "memory": "x"}]}
        assert body["error"] is None

    def test_poll_unknown_event_returns_404(self, client):
        c, _, _ = client
        resp = c.get("/v1/event/00000000-0000-0000-0000-000000000000/")
        assert resp.status_code == 404
