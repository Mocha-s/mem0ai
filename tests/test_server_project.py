"""E2E tests for the OSS ``/project`` endpoint and project-scoped /configure rejection.

This is the first server test in the repo that hits a real (in-memory SQLite)
database. We use Alembic to bring the schema up to head so the tests also
exercise migration ``007`` end-to-end.
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
# GET /project
# ---------------------------------------------------------------------------


class TestGetProject:
    def test_get_returns_seeded_defaults(self, client):
        c, _, _ = client
        resp = c.get("/project")
        assert resp.status_code == 200
        body = resp.json()
        assert body["custom_instructions"] is None
        assert body["custom_categories"] is None
        assert body["retrieval_criteria"] is None
        assert body["multilingual"] is False
        assert body["decay"] is False


# ---------------------------------------------------------------------------
# PATCH /project
# ---------------------------------------------------------------------------


class TestPatchProject:
    def test_patch_persists_retrieval_criteria(self, client):
        c, _, SessionLocal = client
        criteria = [
            {"name": "joy", "description": "positive emotion", "weight": 3},
            {"name": "curiosity", "description": "inquisitive", "weight": 1},
        ]
        resp = c.patch("/project", json={"retrieval_criteria": criteria})
        assert resp.status_code == 200
        assert resp.json()["retrieval_criteria"] == criteria

        # Round-trip through GET
        again = c.get("/project")
        assert again.json()["retrieval_criteria"] == criteria

    def test_patch_persists_all_fields(self, client):
        c, _, _ = client
        resp = c.patch(
            "/project",
            json={
                "custom_instructions": "Focus on dietary preferences.",
                "custom_categories": ["food", {"name": "travel", "description": "trips"}],
                "retrieval_criteria": [{"name": "urgency", "description": "urgent", "weight": 5}],
                "multilingual": True,
                "decay": True,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["custom_instructions"] == "Focus on dietary preferences."
        assert body["custom_categories"] == ["food", {"name": "travel", "description": "trips"}]
        assert body["retrieval_criteria"][0]["name"] == "urgency"
        assert body["multilingual"] is True
        assert body["decay"] is True

    def test_patch_partial_keeps_other_fields(self, client):
        c, _, _ = client
        c.patch("/project", json={"multilingual": True, "decay": True})
        c.patch("/project", json={"custom_instructions": "be terse"})
        body = c.get("/project").json()
        assert body["custom_instructions"] == "be terse"
        assert body["multilingual"] is True
        assert body["decay"] is True

    def test_patch_empty_body_rejected(self, client):
        c, _, _ = client
        resp = c.patch("/project", json={})
        assert resp.status_code == 422  # Pydantic model_validator triggers 422

    def test_patch_unknown_field_rejected(self, client):
        c, _, _ = client
        resp = c.patch("/project", json={"unknown_field": "x"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /configure rejection of project-scoped fields
# ---------------------------------------------------------------------------


class TestConfigureRejectsProjectFields:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("retrieval_criteria", [{"name": "joy", "description": "x", "weight": 1}]),
            ("custom_instructions", "be terse"),
            ("custom_categories", ["food"]),
            ("multilingual", True),
            ("decay", True),
        ],
    )
    def test_configure_rejects_each_project_field(self, client, field, value):
        c, _, _ = client
        resp = c.post("/configure", json={field: value})
        assert resp.status_code == 400
        assert "PATCH /project" in resp.json()["detail"]

    def test_configure_still_accepts_non_project_fields(self, client):
        """Sanity: regular config keys still flow through."""
        c, _, _ = client
        # vector_store / llm / embedder are validated against bundled providers,
        # but a harmless top-level key like ``history_db_path`` should pass.
        resp = c.post("/configure", json={"history_db_path": "/tmp/x.db"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /v3/memories/search/ forwards use_criteria + criteria
# ---------------------------------------------------------------------------


class TestSearchForwardsCriteriaFlags:
    def test_use_criteria_passed_through(self, client):
        c, mock, _ = client
        c.post(
            "/v3/memories/search/",
            json={
                "query": "joy?",
                "filters": {"user_id": "alice"},
                "use_criteria": False,
            },
        )
        assert mock.search.call_args.kwargs["use_criteria"] is False

    def test_criteria_passed_through(self, client):
        c, mock, _ = client
        criteria = [{"name": "joy", "description": "positive", "weight": 3}]
        c.post(
            "/v3/memories/search/",
            json={
                "query": "joy?",
                "filters": {"user_id": "alice"},
                "criteria": criteria,
            },
        )
        assert mock.search.call_args.kwargs["criteria"] == criteria

    def test_unset_criteria_flags_default_to_none(self, client):
        """V3 search always forwards every kwarg from its SearchBody schema;
        unset ``use_criteria`` / ``criteria`` arrive as ``None`` rather than
        being dropped from the call entirely."""
        c, mock, _ = client
        c.post("/v3/memories/search/", json={"query": "x", "filters": {"user_id": "alice"}})
        kwargs = mock.search.call_args.kwargs
        assert kwargs["use_criteria"] is None
        assert kwargs["criteria"] is None
