"""Breaking-change contract: pre-V3 ``/memories`` paths must return 404.

Tasks 6-11 migrated every memory route under ``/v3/memories/*``. This file
pins that migration: every old path that used to hit the FastAPI app is now
a hard 404. The contract is "no matching route" (FastAPI's natural 404), not
an explicit stub — the constraint in Task 12 is that we don't add legacy
shim handlers.

Fixtures (``sqlite_db`` + ``client``) are copied verbatim from
``tests/test_server_project.py:30-99`` so this file can run independently.
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
# Old paths must return 404 — clients must migrate to /v3/memories/*
# ---------------------------------------------------------------------------


class TestOldPathsReturn404:
    @pytest.mark.parametrize("method,path,body", [
        ("post",   "/memories",            {"messages": [{"role": "user", "content": "x"}], "user_id": "alice"}),
        ("post",   "/memories/list",       {"filters": {"user_id": "alice"}}),
        ("post",   "/memories/search",     {"query": "x", "filters": {"user_id": "alice"}}),
        ("get",    "/memories/mem-1",      None),
        ("put",    "/memories/mem-1",      {"text": "y"}),
        ("delete", "/memories/mem-1",      None),
        ("post",   "/memories/delete",     {"filters": {"user_id": "alice"}}),
        ("get",    "/memories/mem-1/history", None),
        ("post",   "/memories/mem-1/feedback", {"feedback": "POSITIVE"}),
    ])
    def test_old_path_returns_404(self, client, method, path, body):
        c, _, _ = client
        if method == "get":
            resp = c.get(path)
        elif method == "delete":
            resp = c.delete(path)
        else:
            resp = getattr(c, method)(path, json=body)
        assert resp.status_code == 404, f"{method.upper()} {path} should be 404 but was {resp.status_code}"
