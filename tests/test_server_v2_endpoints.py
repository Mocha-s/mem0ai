"""E2E tests for V3 server endpoints (formerly v2 endpoints).

These tests run server/main.py through FastAPI's TestClient with Memory mocked
out, asserting the V3 contract:
  - POST /v3/memories/add/ accepts identifiers (user_id/agent_id/run_id/app_id)
    and returns ``{event_id, status, message}``; the SDK Memory.add is called
    by the FastAPI background task that TestClient runs synchronously.
  - POST /v3/memories/ accepts a v2 filter body and forwards it to
    Memory.get_all with pagination kwargs (top_k=page_size, offset, count_total).
  - POST /v3/memories/search/ forwards filters + V3 defaults to Memory.search.
  - POST /v3/memories/delete/ forwards a v2 filter body to Memory.delete_all.
  - The pre-V3 flat-query endpoints (GET /memories, POST /search,
    DELETE /memories) no longer exist — clients hitting them get a 4xx.

Fixtures (``sqlite_db`` + ``client``) are copied verbatim from
``tests/test_server_project.py:30-99`` so this file can run independently and
the V3 add endpoint has a real ``events`` table to insert into.
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


@pytest.fixture
def client(sqlite_db):
    """Build a TestClient backed by SQLite + a mocked Memory."""
    url, engine = sqlite_db
    sys.path.insert(0, str(SERVER_DIR))

    fake_memory = MagicMock()
    fake_memory.get.return_value = {"id": "mem-1", "memory": "x", "user_id": "alice"}
    fake_memory.get_all.return_value = {
        "results": [{"id": "mem-1", "memory": "x", "user_id": "alice"}],
        "count": 1,
    }
    fake_memory.add.return_value = {"results": [{"id": "mem-1", "event": "ADD", "memory": "x"}]}
    fake_memory.search.return_value = [{"id": "mem-1", "memory": "x", "score": 0.9}]
    fake_memory.delete_all.return_value = {"message": "Memories deleted successfully!"}

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
                # Reload auth.py so its module-level constants (AUTH_DISABLED,
                # ADMIN_API_KEY, JWT_SECRET) pick up the env we just patched
                # — ``test_server_auth.py`` reloads auth with various keys, and
                # those values are otherwise sticky across modules.
                import auth as server_auth
                importlib.reload(server_auth)

                import main as server_main

                importlib.reload(server_main)
                server_main.set_session_factory(SessionLocalSqlite)
                server_main.initialize_state(server_main.DEFAULT_CONFIG)
                yield TestClient(server_main.app), fake_memory
    finally:
        sys.path.remove(str(SERVER_DIR))


# ---------------------------------------------------------------------------
# POST /v3/memories/add/ — app_id field + entity-scope check
# ---------------------------------------------------------------------------


class TestAddAppId:
    def test_add_accepts_app_id(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like jazz"}],
            "user_id": "alice",
            "app_id": "music_app",
        })
        assert resp.status_code == 200
        # Response is the async envelope, not {results: [...]}.
        body = resp.json()
        assert "event_id" in body
        # Background task ran synchronously under TestClient, so mock.add was
        # called with the forwarded app_id.
        assert mock.add.call_args.kwargs.get("app_id") == "music_app"

    def test_add_rejects_when_no_identifier(self, client):
        c, _ = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like jazz"}],
        })
        assert resp.status_code == 400
        assert "user_id, agent_id, run_id, app_id" in resp.json()["detail"]

    def test_add_app_id_alone_is_sufficient(self, client):
        c, _ = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "shared event"}],
            "app_id": "team_app",
        })
        assert resp.status_code == 200
        assert "event_id" in resp.json()


# ---------------------------------------------------------------------------
# POST /v3/memories/ — paginated list
# ---------------------------------------------------------------------------


class TestListEndpoint:
    def test_list_forwards_filters(self, client):
        c, mock = client
        resp = c.post("/v3/memories/", json={
            "filters": {"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
        })
        assert resp.status_code == 200
        # V3 list always paginates: forwards top_k=page_size, offset=0,
        # count_total=True. Default page_size is 100.
        mock.get_all.assert_called_once_with(
            filters={"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
            top_k=100,
            offset=0,
            count_total=True,
        )

    def test_list_page_size_passthrough(self, client):
        """``?page_size=50`` replaces the old top-level ``top_k`` body field."""
        c, mock = client
        resp = c.post("/v3/memories/?page_size=50", json={
            "filters": {"user_id": "alice"},
        })
        assert resp.status_code == 200
        kw = mock.get_all.call_args.kwargs
        assert kw["top_k"] == 50
        assert kw["offset"] == 0
        assert kw["count_total"] is True

    def test_list_empty_filters_rejected(self, client):
        """V3 list requires entity-scoped filters; the legacy admin path is gone."""
        c, mock = client
        resp = c.post("/v3/memories/", json={"filters": {}})
        assert resp.status_code == 400
        mock.get_all.assert_not_called()

    def test_list_filters_without_entity_id_rejected(self, client):
        c, mock = client
        resp = c.post("/v3/memories/", json={"filters": {"category": "food"}})
        assert resp.status_code == 400
        mock.get_all.assert_not_called()

    def test_list_value_error_returns_400(self, client):
        c, mock = client
        mock.get_all.side_effect = ValueError("bad filter")
        resp = c.post("/v3/memories/", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 400
        assert "bad filter" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /v3/memories/search/
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    def test_search_forwards_filters(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "music",
            "filters": {"user_id": "alice"},
        })
        assert resp.status_code == 200
        # V3 search always forwards top_k, threshold, rerank, use_criteria,
        # and criteria. Defaults: top_k=10, threshold=0.1, rerank=False.
        kw = mock.search.call_args.kwargs
        assert kw["query"] == "music"
        assert kw["filters"] == {"user_id": "alice"}

    def test_search_forwards_rerank(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "music",
            "filters": {"user_id": "alice"},
            "rerank": True,
        })
        assert resp.status_code == 200
        assert mock.search.call_args.kwargs["rerank"] is True

    def test_search_forwards_top_k_and_threshold(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "music",
            "filters": {"user_id": "alice"},
            "top_k": 5,
            "threshold": 0.5,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["top_k"] == 5
        assert kwargs["threshold"] == 0.5

    def test_search_uses_v3_defaults_when_unset(self, client):
        """V3 always pins defaults rather than letting the SDK resolve them."""
        c, mock = client
        c.post("/v3/memories/search/", json={
            "query": "music",
            "filters": {"user_id": "alice"},
        })
        kwargs = mock.search.call_args.kwargs
        assert kwargs["top_k"] == 10
        assert kwargs["threshold"] == 0.1
        assert kwargs["rerank"] is False


# ---------------------------------------------------------------------------
# POST /v3/memories/delete/
# ---------------------------------------------------------------------------


class TestDeleteEndpoint:
    def test_delete_forwards_filters(self, client):
        c, mock = client
        resp = c.post("/v3/memories/delete/", json={
            "filters": {"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
        })
        assert resp.status_code == 200
        mock.delete_all.assert_called_once_with(
            filters={"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
        )

    def test_delete_rejects_empty_filters(self, client):
        """Empty filters now hit ``_require_entity_scope`` and 400 with the
        v3 detail mentioning the four entity IDs (no longer ``POST /reset``)."""
        c, mock = client
        resp = c.post("/v3/memories/delete/", json={"filters": {}})
        assert resp.status_code == 400
        assert "user_id, agent_id, run_id, app_id" in resp.json()["detail"]
        mock.delete_all.assert_not_called()

    def test_delete_rejects_missing_filters(self, client):
        c, _ = client
        resp = c.post("/v3/memories/delete/", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Pre-v2 endpoints — clients hitting them must see a 4xx (BREAKING change)
# ---------------------------------------------------------------------------


class TestOldEndpointsRemoved:
    @pytest.mark.parametrize("method,path,kwargs", [
        ("GET", "/memories", {"params": {"user_id": "alice"}}),
        ("POST", "/search", {"json": {"query": "x", "user_id": "alice"}}),
        ("DELETE", "/memories", {"params": {"user_id": "alice"}}),
    ])
    def test_old_endpoint_returns_4xx(self, client, method, path, kwargs):
        c, _ = client
        resp = c.request(method, path, **kwargs)
        # FastAPI returns 405 (method not allowed) when path matches a different
        # method, or 404 when the path doesn't exist.
        assert resp.status_code in (404, 405)
