"""E2E tests for ``GET /v1/ping/`` — unauthenticated health probe.

External uptime monitors (load balancers, heartbeat collectors) hit this
route at high frequency without an API key. The contract is:

  - ``200 OK`` always (no DB / LLM dependencies)
  - JSON body identifying the service and major version
  - Reachable WITHOUT an ``X-API-Key`` header even when auth is enabled

Mirrors the fixture pattern from ``test_server_v3_routes.py`` and the
auth-enabled probe pattern from ``test_server_auth.py``.
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


def _build_client(env_overrides: dict, sqlite_url: str, engine) -> TestClient:
    """Reload ``server/main.py`` (and ``auth.py``) with the given env and a
    SQLite-backed SessionLocal, returning a TestClient."""
    sys.path.insert(0, str(SERVER_DIR))
    SessionLocalSqlite = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    base_env = {
        "OPENAI_API_KEY": "fake-key",
        "JWT_SECRET": "test-secret-test-secret-test-secret",
    }
    merged_env = {**base_env, **env_overrides}
    fake_memory = MagicMock()
    try:
        with patch.dict(os.environ, merged_env, clear=False):
            import db as server_db

            server_db.engine = engine
            server_db.SessionLocal = SessionLocalSqlite

            import auth as server_auth
            importlib.reload(server_auth)

            with patch("mem0.Memory.from_config", return_value=fake_memory):
                import main as server_main

                importlib.reload(server_main)
                server_main.set_session_factory(SessionLocalSqlite)
                server_main.initialize_state(server_main.DEFAULT_CONFIG)
                return TestClient(server_main.app)
    finally:
        sys.path.remove(str(SERVER_DIR))


# ---------------------------------------------------------------------------
# GET /v1/ping/
# ---------------------------------------------------------------------------


class TestPingHealthProbe:
    def test_returns_200_without_auth_header_when_auth_disabled(self, sqlite_db):
        client = _build_client(
            {"AUTH_DISABLED": "true", "ADMIN_API_KEY": ""}, *sqlite_db
        )
        resp = client.get("/v1/ping/")
        assert resp.status_code == 200

    def test_returns_200_without_auth_header_when_auth_enabled(self, sqlite_db):
        """The strongest no-auth-required check: ADMIN_API_KEY is set, every
        protected route would 401, but ``/v1/ping/`` must still return 200
        with no ``X-API-Key`` header."""
        client = _build_client(
            {"ADMIN_API_KEY": "test-secret-key-12345"}, *sqlite_db
        )
        resp = client.get("/v1/ping/")
        assert resp.status_code == 200

    def test_response_shape(self, sqlite_db):
        client = _build_client(
            {"AUTH_DISABLED": "true", "ADMIN_API_KEY": ""}, *sqlite_db
        )
        resp = client.get("/v1/ping/")
        body = resp.json()
        assert body == {"status": "ok", "service": "mem0-oss", "version": "v3"}

    def test_content_type_is_json(self, sqlite_db):
        client = _build_client(
            {"AUTH_DISABLED": "true", "ADMIN_API_KEY": ""}, *sqlite_db
        )
        resp = client.get("/v1/ping/")
        assert resp.headers["content-type"].startswith("application/json")
