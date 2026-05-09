"""E2E tests for ``POST /v3/memories/`` — paginated list envelope.

The new V3 list endpoint returns ``{count, next, previous, results}`` and
forwards ``offset`` + ``count_total`` to ``Memory.get_all``. ``filters``
must include at least one of ``user_id`` / ``agent_id`` / ``run_id`` /
``app_id``.
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


class TestListEnvelope:
    def test_returns_count_next_previous_results(self, client):
        c, fake_memory, _ = client
        fake_memory.get_all.return_value = {
            "results": [{"id": f"mem-{i}", "memory": f"m{i}"} for i in range(50)],
            "count": 230,
        }

        resp = c.post("/v3/memories/?page=1&page_size=50", json={
            "filters": {"user_id": "alice"}
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 230
        assert body["previous"] is None
        assert body["next"] is not None and "page=2" in body["next"]
        assert len(body["results"]) == 50

    def test_last_page_has_no_next(self, client):
        c, fake_memory, _ = client
        fake_memory.get_all.return_value = {"results": [{"id": "mem-1"}], "count": 51}
        resp = c.post("/v3/memories/?page=2&page_size=50", json={
            "filters": {"user_id": "alice"}
        })
        body = resp.json()
        assert body["next"] is None
        assert "page=1" in body["previous"]

    def test_empty_filters_returns_400(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/", json={"filters": {}})
        assert resp.status_code == 400

    def test_filters_without_entity_id_returns_400(self, client):
        c, _, _ = client
        resp = c.post("/v3/memories/", json={"filters": {"category": "food"}})
        assert resp.status_code == 400

    def test_forwards_offset_and_count_total_to_sdk(self, client):
        c, fake_memory, _ = client
        fake_memory.get_all.return_value = {"results": [], "count": 0}
        c.post("/v3/memories/?page=3&page_size=20", json={"filters": {"user_id": "alice"}})
        kw = fake_memory.get_all.call_args.kwargs
        assert kw["offset"] == 40
        assert kw["top_k"] == 20
        assert kw["count_total"] is True
