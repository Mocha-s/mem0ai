"""End-to-end happy-path test for the V3 OSS REST contract.

This file exercises the full V3 lifecycle through one ``TestClient`` instance,
in the order a real client would invoke the API:

    add (async)  ->  poll event  ->  list  ->  search
                ->  get / update / history / feedback / delete
                ->  bulk delete  ->  pre-V3 paths return 404

Fixtures (``sqlite_db`` + ``client``) are copied verbatim from
``tests/test_server_project.py:30-99`` so this file boots its own fresh
schema and reloads ``server.main`` against a mocked ``Memory``. ``TestClient``
runs FastAPI ``BackgroundTasks`` synchronously after the response is sent, so
the async-add worker observably completes before the next request fires.
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
    fake_memory.search.return_value = {"results": [{"id": "mem-1", "memory": "x", "score": 0.9}]}
    # Default add() return must match what the V3 worker persists into Event.result.
    fake_memory.add.return_value = {"results": [{"id": "mem-1", "event": "ADD", "memory": "I love jazz"}]}

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
# Happy-path E2E flow
# ---------------------------------------------------------------------------


class TestV3HappyPathFlow:
    """One method, eleven steps, in the order a real client would call them."""

    def test_full_lifecycle(self, client):
        c, fake_memory, _ = client

        # -------------------------------------------------------------------
        # STEP 1: POST /v3/memories/add/ — async add returns event_id
        # -------------------------------------------------------------------
        add_resp = c.post(
            "/v3/memories/add/",
            json={
                "messages": [{"role": "user", "content": "I love jazz"}],
                "user_id": "alice",
            },
        )
        assert add_resp.status_code == 200, add_resp.text
        add_body = add_resp.json()
        assert "event_id" in add_body and add_body["event_id"]
        assert "status" in add_body
        # TestClient runs BackgroundTasks synchronously, so by the time we
        # see the response the worker has already completed.
        assert add_body["status"] in {"PENDING", "SUCCEEDED"}
        event_id = add_body["event_id"]

        # -------------------------------------------------------------------
        # STEP 2: GET /v1/event/{event_id}/ — poll returns SUCCEEDED + result
        # -------------------------------------------------------------------
        poll_resp = c.get(f"/v1/event/{event_id}/")
        assert poll_resp.status_code == 200, poll_resp.text
        poll_body = poll_resp.json()
        assert poll_body["event_id"] == event_id
        assert poll_body["status"] in {"PENDING", "SUCCEEDED"}
        # TestClient ran the BackgroundTask synchronously, so by now status
        # must be SUCCEEDED and the SDK return is mirrored on result.
        assert poll_body["status"] == "SUCCEEDED"
        assert poll_body["result"] == {
            "results": [{"id": "mem-1", "event": "ADD", "memory": "I love jazz"}]
        }
        assert poll_body["error"] is None

        # -------------------------------------------------------------------
        # STEP 3: POST /v3/memories/ — paginated list envelope
        # -------------------------------------------------------------------
        # 23 total memories at page_size=10 => page 1 has 10 results, next
        # links to page 2, previous is None (we're on page 1).
        fake_memory.get_all.return_value = {
            "results": [{"id": f"mem-{i}", "memory": f"m{i}"} for i in range(10)],
            "count": 23,
        }
        list_resp = c.post(
            "/v3/memories/?page=1&page_size=10",
            json={"filters": {"user_id": "alice"}},
        )
        assert list_resp.status_code == 200, list_resp.text
        list_body = list_resp.json()
        assert set(list_body.keys()) == {"count", "next", "previous", "results"}
        assert list_body["count"] == 23
        assert len(list_body["results"]) == 10
        assert list_body["previous"] is None
        assert list_body["next"] is not None
        assert "page=2" in list_body["next"]
        # SDK call: page=1 => offset=0, page_size=10 => top_k=10
        list_kwargs = fake_memory.get_all.call_args.kwargs
        assert list_kwargs["filters"] == {"user_id": "alice"}
        assert list_kwargs["top_k"] == 10
        assert list_kwargs["offset"] == 0
        assert list_kwargs["count_total"] is True

        # -------------------------------------------------------------------
        # STEP 4: POST /v3/memories/search/ — hybrid retrieval
        # -------------------------------------------------------------------
        fake_memory.search.return_value = {
            "results": [{"id": "mem-1", "memory": "jazz", "score": 0.9}]
        }
        search_resp = c.post(
            "/v3/memories/search/",
            json={"query": "jazz", "filters": {"user_id": "alice"}},
        )
        assert search_resp.status_code == 200, search_resp.text
        search_body = search_resp.json()
        assert "results" in search_body
        assert search_body["results"] == [{"id": "mem-1", "memory": "jazz", "score": 0.9}]
        # V3 defaults: top_k=10, threshold=0.1, rerank=False
        search_kwargs = fake_memory.search.call_args.kwargs
        assert search_kwargs["query"] == "jazz"
        assert search_kwargs["filters"] == {"user_id": "alice"}
        assert search_kwargs["top_k"] == 10
        assert search_kwargs["threshold"] == 0.1
        assert search_kwargs["rerank"] is False

        # -------------------------------------------------------------------
        # STEP 5: GET /v3/memories/{id}/ — single-memory read
        # -------------------------------------------------------------------
        fake_memory.get.return_value = {"id": "mem-1", "memory": "jazz"}
        get_resp = c.get("/v3/memories/mem-1/")
        assert get_resp.status_code == 200, get_resp.text
        get_body = get_resp.json()
        assert get_body["id"] == "mem-1"
        assert get_body["memory"] == "jazz"

        # -------------------------------------------------------------------
        # STEP 6: PUT /v3/memories/{id}/ — update content
        # -------------------------------------------------------------------
        fake_memory.update.return_value = {"id": "mem-1", "memory": "blues"}
        put_resp = c.put("/v3/memories/mem-1/", json={"text": "blues"})
        assert put_resp.status_code == 200, put_resp.text
        put_body = put_resp.json()
        assert put_body["memory"] == "blues"
        update_kwargs = fake_memory.update.call_args.kwargs
        assert update_kwargs["memory_id"] == "mem-1"
        assert update_kwargs["data"] == "blues"

        # -------------------------------------------------------------------
        # STEP 7: GET /v3/memories/{id}/history/ — change history
        # -------------------------------------------------------------------
        fake_memory.history.return_value = [
            {"event": "UPDATE", "id": "mem-1", "old_memory": "jazz", "new_memory": "blues"}
        ]
        hist_resp = c.get("/v3/memories/mem-1/history/")
        assert hist_resp.status_code == 200, hist_resp.text
        hist_body = hist_resp.json()
        assert isinstance(hist_body, list)
        assert hist_body[0]["event"] == "UPDATE"

        # -------------------------------------------------------------------
        # STEP 8: POST /v3/memories/{id}/feedback/ — record feedback
        # -------------------------------------------------------------------
        fb_resp = c.post(
            "/v3/memories/mem-1/feedback/",
            json={"feedback": "POSITIVE"},
        )
        assert fb_resp.status_code == 200, fb_resp.text
        fake_memory.feedback.assert_called_once()

        # -------------------------------------------------------------------
        # STEP 9: DELETE /v3/memories/{id}/ — single delete
        # -------------------------------------------------------------------
        del_resp = c.delete("/v3/memories/mem-1/")
        assert del_resp.status_code == 200, del_resp.text
        fake_memory.delete.assert_called_once()

        # -------------------------------------------------------------------
        # STEP 10: POST /v3/memories/delete/ — bulk delete by filters
        # -------------------------------------------------------------------
        bulk_resp = c.post(
            "/v3/memories/delete/",
            json={"filters": {"user_id": "alice"}},
        )
        assert bulk_resp.status_code == 200, bulk_resp.text
        fake_memory.delete_all.assert_called_once()
        bulk_kwargs = fake_memory.delete_all.call_args.kwargs
        assert bulk_kwargs["filters"] == {"user_id": "alice"}

        # -------------------------------------------------------------------
        # STEP 11: pre-V3 paths must return 404 (no legacy shims)
        # -------------------------------------------------------------------
        legacy_add = c.post(
            "/memories",
            json={
                "messages": [{"role": "user", "content": "I love jazz"}],
                "user_id": "alice",
            },
        )
        assert legacy_add.status_code == 404

        legacy_list = c.post("/memories/list", json={"filters": {"user_id": "alice"}})
        assert legacy_list.status_code == 404

        legacy_search = c.post(
            "/memories/search",
            json={"query": "jazz", "filters": {"user_id": "alice"}},
        )
        assert legacy_search.status_code == 404


# ---------------------------------------------------------------------------
# Negative-path coverage
# ---------------------------------------------------------------------------


class TestV3NegativePaths:
    """Sanity-check that the V3 contract rejects malformed input the way the
    docs claim (400 for entity-scope checks, 422 for missing required fields,
    404 for unknown event IDs)."""

    def test_add_without_entity_id_returns_400(self, client):
        c, _, _ = client
        resp = c.post(
            "/v3/memories/add/",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
        assert resp.status_code == 400, resp.text

    def test_search_without_filters_returns_422(self, client):
        c, _, _ = client
        # No ``filters`` field at all => Pydantic missing-required => 422.
        resp = c.post("/v3/memories/search/", json={"query": "jazz"})
        assert resp.status_code == 422, resp.text

    def test_search_with_empty_filters_returns_400(self, client):
        c, _, _ = client
        # ``filters`` present but no entity ID => entity-scope check => 400.
        resp = c.post(
            "/v3/memories/search/",
            json={"query": "jazz", "filters": {}},
        )
        assert resp.status_code == 400, resp.text

    def test_poll_unknown_event_returns_404(self, client):
        c, _, _ = client
        resp = c.get("/v1/event/00000000-0000-0000-0000-000000000000/")
        assert resp.status_code == 404, resp.text
