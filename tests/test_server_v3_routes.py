"""E2E tests for V3 memory routes that don't have their own dedicated file.

Currently covers:
  - ``POST /v3/memories/search/`` — V3 search defaults + filter-required Pydantic
    contract. The SDK underneath already implements hybrid retrieval (semantic
    + BM25 + entity boost) for pgvector; this file just pins the wire contract.

Fixtures (``sqlite_db`` + ``client``) are copied verbatim from
``tests/test_server_project.py:30-99`` so each V3 test file boots its own
fresh schema and reloads ``server.main`` against a mocked ``Memory``.
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
                # set_session_factory was called inside reload via initialize_state,
                # but server_state imported the *old* SessionLocal — refresh it.
                server_main.set_session_factory(SessionLocalSqlite)
                server_main.initialize_state(server_main.DEFAULT_CONFIG)
                yield TestClient(server_main.app), fake_memory, SessionLocalSqlite
    finally:
        sys.path.remove(str(SERVER_DIR))


# ---------------------------------------------------------------------------
# POST /v3/memories/search/
# ---------------------------------------------------------------------------


class TestSearchDefaults:
    def test_filters_required_returns_422(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/search/", json={"query": "jazz"})
        assert resp.status_code == 422  # Pydantic missing required

    def test_empty_filters_returns_400(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/search/", json={"query": "jazz", "filters": {}})
        assert resp.status_code == 400

    def test_defaults_threshold_rerank_top_k(self, client):
        c, fake_memory, _ = client
        fake_memory.search.return_value = {"results": []}
        c.post("/v3/memories/search/", json={"query": "jazz", "filters": {"user_id": "alice"}})
        kw = fake_memory.search.call_args.kwargs
        assert kw["top_k"] == 10
        assert kw["threshold"] == 0.1
        assert kw["rerank"] is False

    def test_overrides_forwarded(self, client):
        c, fake_memory, _ = client
        fake_memory.search.return_value = {"results": []}
        c.post("/v3/memories/search/", json={
            "query": "jazz",
            "filters": {"user_id": "alice"},
            "top_k": 25,
            "threshold": 0.4,
            "rerank": True,
            "use_criteria": True,
            "criteria": [{"name": "joy", "description": "x", "weight": 2}],
        })
        kw = fake_memory.search.call_args.kwargs
        assert kw["top_k"] == 25
        assert kw["threshold"] == 0.4
        assert kw["rerank"] is True
        assert kw["use_criteria"] is True
        assert kw["criteria"][0]["name"] == "joy"


# ---------------------------------------------------------------------------
# GET/PUT/DELETE /v3/memories/{memory_id}/, POST /v3/memories/delete/,
# GET /v3/memories/{memory_id}/history/, POST /v3/memories/{memory_id}/feedback/
# ---------------------------------------------------------------------------


class TestV3MemoryCRUD:
    def test_get_memory_by_id(self, client):
        c, fake_memory, _ = client
        fake_memory.get.return_value = {"id": "mem-1", "memory": "x"}
        resp = c.get("/v3/memories/mem-1/")
        assert resp.status_code == 200
        assert resp.json()["id"] == "mem-1"

    def test_put_updates_memory(self, client):
        c, fake_memory, _ = client
        fake_memory.update.return_value = {"id": "mem-1", "memory": "y"}
        resp = c.put("/v3/memories/mem-1/", json={"text": "y"})
        assert resp.status_code == 200
        kw = fake_memory.update.call_args.kwargs
        assert kw["data"] == "y"

    def test_delete_memory(self, client):
        c, fake_memory, _ = client
        resp = c.delete("/v3/memories/mem-1/")
        assert resp.status_code == 200

    def test_history_endpoint(self, client):
        c, fake_memory, _ = client
        fake_memory.history.return_value = []
        resp = c.get("/v3/memories/mem-1/history/")
        assert resp.status_code == 200

    def test_feedback_endpoint(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/mem-1/feedback/", json={
            "feedback": "POSITIVE", "feedback_reason": "useful"
        })
        assert resp.status_code == 200

    def test_bulk_delete_requires_filters(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/delete/", json={"filters": {}})
        assert resp.status_code == 400

    def test_bulk_delete_with_filters(self, client):
        c, fake_memory, _ = client
        resp = c.post("/v3/memories/delete/", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 200
