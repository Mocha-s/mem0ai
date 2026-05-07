"""E2E tests for the v2 server endpoints.

These tests run server/main.py through FastAPI's TestClient with Memory mocked
out, asserting the v2 contract:
  - POST /memories accepts the new ``app_id`` field
  - POST /memories/list accepts a v2 filter body and forwards it to Memory.get_all
  - POST /memories/search forwards filters + rerank to Memory.search
  - POST /memories/delete forwards a v2 filter body to Memory.delete_all
  - The old flat-query endpoints (GET /memories, POST /search, DELETE /memories)
    no longer exist — clients hitting them get a 4xx
"""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient


@pytest.fixture
def _mock_memory():
    mock_instance = MagicMock()
    mock_instance.get.return_value = {"id": "mem-1", "memory": "x", "user_id": "alice"}
    mock_instance.get_all.return_value = {"results": [{"id": "mem-1", "memory": "x", "user_id": "alice"}]}
    mock_instance.add.return_value = {"results": [{"id": "mem-1", "event": "ADD", "memory": "x"}]}
    mock_instance.search.return_value = [{"id": "mem-1", "memory": "x", "score": 0.9}]
    mock_instance.delete_all.return_value = {"message": "Memories deleted successfully!"}
    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key", "ADMIN_API_KEY": ""}):
        with patch("mem0.Memory.from_config", return_value=mock_instance):
            yield mock_instance


@pytest.fixture
def client(_mock_memory):
    import server.main as server_main
    importlib.reload(server_main)
    return TestClient(server_main.app), _mock_memory


# ---------------------------------------------------------------------------
# POST /memories — app_id field
# ---------------------------------------------------------------------------


class TestAddAppId:
    def test_add_accepts_app_id(self, client):
        c, mock = client
        resp = c.post("/memories", json={
            "messages": [{"role": "user", "content": "I like jazz"}],
            "user_id": "alice",
            "app_id": "music_app",
        })
        assert resp.status_code == 200
        # add forwards app_id to the SDK
        assert mock.add.call_args.kwargs.get("app_id") == "music_app"

    def test_add_rejects_when_no_identifier(self, client):
        c, _ = client
        resp = c.post("/memories", json={
            "messages": [{"role": "user", "content": "I like jazz"}],
        })
        assert resp.status_code == 400
        assert "user_id, agent_id, run_id, app_id" in resp.json()["detail"]

    def test_add_app_id_alone_is_sufficient(self, client):
        c, _ = client
        resp = c.post("/memories", json={
            "messages": [{"role": "user", "content": "shared event"}],
            "app_id": "team_app",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /memories/list
# ---------------------------------------------------------------------------


class TestListEndpoint:
    def test_list_forwards_filters(self, client):
        c, mock = client
        resp = c.post("/memories/list", json={
            "filters": {"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
        })
        assert resp.status_code == 200
        mock.get_all.assert_called_once_with(
            filters={"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
            top_k=1000,
        )

    def test_list_top_k_passthrough(self, client):
        c, mock = client
        resp = c.post("/memories/list", json={
            "filters": {"user_id": "alice"},
            "top_k": 50,
        })
        assert resp.status_code == 200
        assert mock.get_all.call_args.kwargs["top_k"] == 50

    def test_list_empty_filters_uses_admin_path(self, client):
        c, mock = client
        # Empty filters is allowed and bypasses get_all's required-id check
        resp = c.post("/memories/list", json={"filters": {}})
        assert resp.status_code == 200
        mock.get_all.assert_not_called()
        mock.vector_store.list.assert_called_once()

    def test_list_value_error_returns_400(self, client):
        c, mock = client
        mock.get_all.side_effect = ValueError("bad filter")
        resp = c.post("/memories/list", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 400
        assert "bad filter" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /memories/search
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    def test_search_forwards_filters(self, client):
        c, mock = client
        resp = c.post("/memories/search", json={
            "query": "music",
            "filters": {"user_id": "alice"},
        })
        assert resp.status_code == 200
        mock.search.assert_called_once_with(
            query="music",
            filters={"user_id": "alice"},
        )

    def test_search_forwards_rerank(self, client):
        c, mock = client
        resp = c.post("/memories/search", json={
            "query": "music",
            "filters": {"user_id": "alice"},
            "rerank": True,
        })
        assert resp.status_code == 200
        assert mock.search.call_args.kwargs["rerank"] is True

    def test_search_forwards_top_k_and_threshold(self, client):
        c, mock = client
        resp = c.post("/memories/search", json={
            "query": "music",
            "filters": {"user_id": "alice"},
            "top_k": 5,
            "threshold": 0.5,
        })
        assert resp.status_code == 200
        kwargs = mock.search.call_args.kwargs
        assert kwargs["top_k"] == 5
        assert kwargs["threshold"] == 0.5

    def test_search_omits_unset_kwargs(self, client):
        """Don't pass None for unset fields — let the SDK use its own defaults."""
        c, mock = client
        c.post("/memories/search", json={
            "query": "music",
            "filters": {"user_id": "alice"},
        })
        kwargs = mock.search.call_args.kwargs
        assert "rerank" not in kwargs
        assert "top_k" not in kwargs
        assert "threshold" not in kwargs


# ---------------------------------------------------------------------------
# POST /memories/delete
# ---------------------------------------------------------------------------


class TestDeleteEndpoint:
    def test_delete_forwards_filters(self, client):
        c, mock = client
        resp = c.post("/memories/delete", json={
            "filters": {"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
        })
        assert resp.status_code == 200
        mock.delete_all.assert_called_once_with(
            filters={"AND": [{"user_id": "alice"}, {"app_id": "ios"}]},
        )

    def test_delete_rejects_empty_filters(self, client):
        c, mock = client
        resp = c.post("/memories/delete", json={"filters": {}})
        assert resp.status_code == 400
        assert "POST /reset" in resp.json()["detail"]
        mock.delete_all.assert_not_called()

    def test_delete_rejects_missing_filters(self, client):
        c, _ = client
        # Pydantic should reject the request entirely since filters is required
        resp = c.post("/memories/delete", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Removed endpoints — clients hitting them must see a 4xx (BREAKING change)
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
