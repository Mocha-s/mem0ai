"""Tests for REST API parameter forwarding (V3 routes).

Verifies that the Pydantic request models in server/main.py correctly accept
and forward all parameters supported by the underlying Memory class methods,
including top_k, threshold, infer, memory_type, prompt, and the v2 filter dict.

Routes under test (post-V3):
  - POST /v3/memories/add/      (async — Memory.add invoked via background task)
  - POST /v3/memories/search/   (V3 defaults: top_k=10, threshold=0.1, rerank=False)
  - POST /v3/memories/          (paginated list)
  - PUT  /v3/memories/{id}/     (text + metadata forwarding)

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    fake_memory.add.return_value = {"results": [{"id": "mem-1", "event": "ADD", "memory": "test"}]}
    fake_memory.search.return_value = [{"id": "mem-1", "memory": "test", "score": 0.9}]
    fake_memory.get.return_value = {"id": "mem-1", "memory": "test memory"}
    fake_memory.get_all.return_value = {"results": [{"id": "mem-1", "memory": "test memory"}], "count": 1}
    fake_memory.update.return_value = {"message": "Memory updated"}
    fake_memory.history.return_value = [{"id": "mem-1", "old_memory": "a", "new_memory": "b"}]
    fake_memory.delete.return_value = None
    fake_memory.delete_all.return_value = {"message": "Memories deleted"}
    fake_memory.reset.return_value = None

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


# ===========================================================================
# SearchBody: top_k parameter (POST /v3/memories/search/)
# ===========================================================================


class TestSearchLimit:
    """Verify that the top_k parameter is accepted and forwarded to Memory.search()."""

    def test_limit_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "top_k": 5,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["top_k"] == 5

    def test_limit_one(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "top_k": 1,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["top_k"] == 1

    def test_limit_omitted_uses_v3_default(self, client):
        """When top_k is unset, V3 pins it to its own default (10) and
        forwards that explicitly to Memory.search()."""
        c, mock = client
        resp = c.post("/v3/memories/search/", json={"query": "food", "filters": {"user_id": "u1"}})
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["top_k"] == 10


# ===========================================================================
# SearchBody: threshold parameter
# ===========================================================================


class TestSearchThreshold:
    """Verify that the threshold parameter is accepted and forwarded."""

    def test_threshold_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "threshold": 0.8,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["threshold"] == 0.8

    def test_threshold_zero(self, client):
        """threshold=0.0 is a valid falsy value that must not be filtered out."""
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "threshold": 0.0,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["threshold"] == 0.0

    def test_threshold_omitted_uses_v3_default(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={"query": "food", "filters": {"user_id": "u1"}})
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["threshold"] == 0.1


# ===========================================================================
# SearchBody: top_k + threshold together
# ===========================================================================


class TestSearchLimitAndThreshold:
    def test_both_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "top_k": 10, "threshold": 0.5,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["top_k"] == 10
        assert kwargs["threshold"] == 0.5


# ===========================================================================
# MemoryCreate: infer parameter (POST /v3/memories/add/ via background task)
# ===========================================================================


class TestAddInfer:
    """Verify that the infer parameter is accepted and forwarded to Memory.add()."""

    def test_infer_false_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "Store this exactly"}],
            "user_id": "u1",
            "infer": False,
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["infer"] is False

    def test_infer_true_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like pizza"}],
            "user_id": "u1",
            "infer": True,
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["infer"] is True

    def test_infer_omitted_uses_memory_default(self, client):
        """When infer is not sent, model_dump(exclude_none=True) drops it,
        so the SDK Memory.add() picks its own default (True)."""
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "hello"}],
            "user_id": "u1",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert "infer" not in kwargs


# ===========================================================================
# MemoryCreate: memory_type parameter
# ===========================================================================


class TestAddMemoryType:
    """Verify that the memory_type parameter is accepted and forwarded."""

    def test_memory_type_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like pizza"}],
            "user_id": "u1",
            "memory_type": "core",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["memory_type"] == "core"

    def test_memory_type_omitted(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "hello"}],
            "user_id": "u1",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert "memory_type" not in kwargs


# ===========================================================================
# MemoryCreate: prompt parameter
# ===========================================================================


class TestAddPrompt:
    """Verify that the prompt parameter is accepted and forwarded."""

    def test_prompt_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like pizza"}],
            "user_id": "u1",
            "prompt": "Extract food preferences only.",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["prompt"] == "Extract food preferences only."

    def test_prompt_omitted(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "hello"}],
            "user_id": "u1",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert "prompt" not in kwargs


# ===========================================================================
# MemoryCreate: all new params together
# ===========================================================================


class TestAddAllNewParams:
    def test_infer_memory_type_and_prompt_together(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like pizza"}],
            "user_id": "u1",
            "infer": False,
            "memory_type": "core",
            "prompt": "Custom extraction prompt.",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["infer"] is False
        assert kwargs["memory_type"] == "core"
        assert kwargs["prompt"] == "Custom extraction prompt."


# ===========================================================================
# Edge cases: falsy-but-valid values must not be filtered out
# ===========================================================================


class TestFalsyValues:
    """The handler filters with ``model_dump(exclude_none=True)``. Falsy
    values like False, 0, 0.0, and empty string must still be forwarded."""

    def test_infer_false_not_filtered(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "infer": False,
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["infer"] is False

    def test_threshold_zero_not_filtered(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "threshold": 0.0,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["threshold"] == 0.0


# ===========================================================================
# Extra/unknown fields are still silently ignored (existing Pydantic behavior)
# ===========================================================================


class TestUnknownFieldsIgnored:
    def test_unknown_search_field_ignored(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "bogus_field": "xyz",
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert "bogus_field" not in kwargs

    def test_unknown_add_field_ignored(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "unknown_param": 42,
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert "unknown_param" not in kwargs


# ===========================================================================
# Backward compatibility: existing params still work
# ===========================================================================


class TestExistingParamsUnchanged:
    def test_search_filters_still_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food",
            "filters": {"AND": [{"user_id": "u1"}, {"agent_id": "a1"}, {"category": "food"}]},
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        # The whole v2 filter dict is passed through verbatim — the SDK is
        # responsible for translating it into the vector_store filter form.
        assert kwargs["filters"] == {"AND": [
            {"user_id": "u1"}, {"agent_id": "a1"}, {"category": "food"}
        ]}

    def test_add_metadata_still_forwarded(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "agent_id": "a1",
            "metadata": {"source": "test"},
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["user_id"] == "u1"
        assert kwargs["agent_id"] == "a1"
        assert kwargs["metadata"] == {"source": "test"}


# ===========================================================================
# OpenAPI schema: new fields are documented
# ===========================================================================


class TestOpenAPISchema:
    """Verify the new fields appear in the auto-generated OpenAPI schema."""

    def test_search_schema_includes_top_k(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        search_props = schema["components"]["schemas"]["SearchBody"]["properties"]
        assert "top_k" in search_props

    def test_search_schema_includes_threshold(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        search_props = schema["components"]["schemas"]["SearchBody"]["properties"]
        assert "threshold" in search_props

    def test_search_schema_includes_rerank(self, client):
        """rerank field, surfaced in v2 alignment."""
        c, _ = client
        schema = c.get("/openapi.json").json()
        search_props = schema["components"]["schemas"]["SearchBody"]["properties"]
        assert "rerank" in search_props

    def test_search_schema_includes_filters(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        search_props = schema["components"]["schemas"]["SearchBody"]["properties"]
        assert "filters" in search_props

    def test_add_schema_includes_infer(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        add_props = schema["components"]["schemas"]["MemoryCreate"]["properties"]
        assert "infer" in add_props

    def test_add_schema_includes_memory_type(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        add_props = schema["components"]["schemas"]["MemoryCreate"]["properties"]
        assert "memory_type" in add_props

    def test_add_schema_includes_prompt(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        add_props = schema["components"]["schemas"]["MemoryCreate"]["properties"]
        assert "prompt" in add_props

    def test_add_schema_includes_app_id(self, client):
        """app_id field, added in v2 alignment."""
        c, _ = client
        schema = c.get("/openapi.json").json()
        add_props = schema["components"]["schemas"]["MemoryCreate"]["properties"]
        assert "app_id" in add_props


# ===========================================================================
# Pydantic type validation: invalid types return 422
# ===========================================================================


class TestTypeValidation:
    """Verify FastAPI/Pydantic rejects invalid types with 422."""

    def test_limit_string_rejected(self, client):
        c, _ = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "top_k": "not_a_number",
        })
        assert resp.status_code == 422

    def test_threshold_string_rejected(self, client):
        c, _ = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "threshold": "high",
        })
        assert resp.status_code == 422

    def test_infer_string_coerced_by_pydantic(self, client):
        """Pydantic v2 coerces truthy strings like 'yes' to True for bool fields."""
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "infer": "yes",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert kwargs["infer"] is True

    def test_infer_invalid_value_rejected(self, client):
        """A value that cannot be coerced to bool should be rejected."""
        c, _ = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "infer": [1, 2, 3],
        })
        assert resp.status_code == 422

    def test_limit_float_rejected(self, client):
        c, _ = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food", "filters": {"user_id": "u1"}, "top_k": 5.7,
        })
        assert resp.status_code == 422

    def test_memory_type_int_rejected(self, client):
        c, _ = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "memory_type": 123,
        })
        assert resp.status_code == 422


# ===========================================================================
# Explicit null values: optional add fields treated as omitted via exclude_none
# ===========================================================================


class TestExplicitNull:
    """When a client sends null for an optional add field, ``model_dump(exclude_none=True)``
    drops it — the SDK Memory class default is used. (V3 search non-nullable
    fields with their own defaults reject null at the Pydantic layer.)"""

    def test_infer_null_uses_memory_default(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "infer": None,
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert "infer" not in kwargs

    def test_prompt_null_uses_memory_default(self, client):
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "test"}],
            "user_id": "u1",
            "prompt": None,
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert "prompt" not in kwargs


# ===========================================================================
# Verify exact call signatures match Memory method params
# ===========================================================================


class TestCallSignatureMatch:
    """Ensure forwarded params exactly match Memory.add() and Memory.search()
    keyword argument names — a typo here would cause a TypeError at runtime."""

    def test_search_kwargs_are_valid(self, client):
        """All kwargs forwarded to Memory.search() must be in its signature.

        V3 search always forwards top_k/threshold/rerank/use_criteria/criteria
        (with their schema defaults), so the valid set widens accordingly."""
        c, mock = client
        resp = c.post("/v3/memories/search/", json={
            "query": "food",
            "filters": {"AND": [{"user_id": "u1"}, {"agent_id": "a1"}, {"run_id": "r1"}]},
            "top_k": 10, "threshold": 0.5, "rerank": True,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        valid_params = {"query", "filters", "top_k", "threshold", "rerank", "use_criteria", "criteria"}
        for key in kwargs:
            assert key in valid_params, f"Unexpected kwarg '{key}' forwarded to Memory.search()"

    def test_add_kwargs_are_valid(self, client):
        """All kwargs forwarded to Memory.add() must be in its signature."""
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "hi"}],
            "user_id": "u1", "agent_id": "a1", "run_id": "r1", "app_id": "ios",
            "metadata": {"k": "v"},
            "infer": False, "memory_type": "core", "prompt": "custom",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        valid_params = {
            "messages", "user_id", "agent_id", "run_id", "app_id", "metadata",
            "infer", "memory_type", "prompt", "timestamp",
        }
        for key in kwargs:
            assert key in valid_params, f"Unexpected kwarg '{key}' forwarded to Memory.add()"

    def test_messages_excluded_from_params_dict(self, client):
        """messages is passed separately via messages= kwarg, not duplicated from model_dump."""
        c, mock = client
        resp = c.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "hi"}],
            "user_id": "u1",
        })
        assert resp.status_code == 200
        kwargs = mock.add.call_args.kwargs
        assert "messages" in kwargs
        assert isinstance(kwargs["messages"], list)
        assert kwargs["messages"][0] == {"role": "user", "content": "hi"}

    def test_query_passed_explicitly(self, client):
        """query is passed as an explicit keyword arg to Memory.search()."""
        c, mock = client
        resp = c.post("/v3/memories/search/", json={"query": "food", "filters": {"user_id": "u1"}})
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["query"] == "food"


# ===========================================================================
# MemoryUpdate: text and metadata forwarding (PUT /v3/memories/{id}/)
# ===========================================================================


class TestUpdateMemory:
    """Verify that PUT /v3/memories/{id}/ extracts text and metadata from the
    request body and forwards them correctly to Memory.update()."""

    def test_text_forwarded_as_data(self, client):
        c, mock = client
        resp = c.put("/v3/memories/mem-1/", json={"text": "Likes tennis"})
        assert resp.status_code == 200
        kwargs = mock.update.call_args.kwargs
        assert kwargs["data"] == "Likes tennis"

    def test_metadata_forwarded(self, client):
        c, mock = client
        resp = c.put("/v3/memories/mem-1/", json={
            "text": "Likes tennis",
            "metadata": {"category": "sports"},
        })
        assert resp.status_code == 200
        kwargs = mock.update.call_args.kwargs
        assert kwargs["metadata"] == {"category": "sports"}

    def test_metadata_omitted_passes_none(self, client):
        c, mock = client
        resp = c.put("/v3/memories/mem-1/", json={"text": "Likes tennis"})
        assert resp.status_code == 200
        kwargs = mock.update.call_args.kwargs
        assert kwargs["metadata"] is None

    def test_missing_text_returns_422(self, client):
        """text is required — omitting it should fail validation."""
        c, _ = client
        resp = c.put("/v3/memories/mem-1/", json={"metadata": {"k": "v"}})
        assert resp.status_code == 422

    def test_dict_not_passed_as_data(self, client):
        """Regression test for #3933: the entire dict must NOT be passed as data."""
        c, mock = client
        resp = c.put("/v3/memories/mem-1/", json={"text": "updated content"})
        assert resp.status_code == 200
        kwargs = mock.update.call_args.kwargs
        assert isinstance(kwargs["data"], str)


class TestUpdateOpenAPISchema:
    """Verify the MemoryUpdate schema appears in the OpenAPI docs."""

    def test_update_schema_includes_text(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        update_props = schema["components"]["schemas"]["MemoryUpdate"]["properties"]
        assert "text" in update_props

    def test_update_schema_includes_metadata(self, client):
        c, _ = client
        schema = c.get("/openapi.json").json()
        update_props = schema["components"]["schemas"]["MemoryUpdate"]["properties"]
        assert "metadata" in update_props


# ===========================================================================
# ListBody: v2 filter forwarding (POST /v3/memories/)
# ===========================================================================


class TestListMemories:
    """Verify that POST /v3/memories/ forwards the v2 filter dict to get_all()."""

    def test_list_forwards_filters(self, client):
        """The user-supplied v2 filter dict reaches get_all() unchanged."""
        c, mock = client
        response = c.post("/v3/memories/", json={
            "filters": {"user_id": "test_routing_user"},
        })
        assert response.status_code == 200
        # V3 envelope is {count, next, previous, results}.
        body = response.json()
        assert isinstance(body.get("results"), list)
        assert "count" in body
        kwargs = mock.get_all.call_args.kwargs
        assert kwargs["filters"] == {"user_id": "test_routing_user"}

    def test_list_forwards_advanced_filters(self, client):
        """AND/OR/NOT and operator dicts are forwarded as-is — translation is the SDK's job."""
        c, mock = client
        body = {
            "filters": {
                "AND": [
                    {"user_id": "u1"},
                    {"OR": [{"agent_id": "a1"}, {"agent_id": "a2"}]},
                ]
            }
        }
        response = c.post("/v3/memories/", json=body)
        assert response.status_code == 200
        kwargs = mock.get_all.call_args.kwargs
        assert kwargs["filters"] == body["filters"]
