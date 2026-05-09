"""V3 route helpers: entity-scope checks, page URL builder."""

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
pytest.importorskip("fastapi", reason="fastapi not installed")

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO_ROOT / "server"


@pytest.fixture
def main_module():
    sys.path.insert(0, str(SERVER_DIR))
    env = {
        "OPENAI_API_KEY": "fake-key",
        "AUTH_DISABLED": "true",
        "JWT_SECRET": "test-secret-test-secret-test-secret",
        # Fast-fail postgres so initialize_state()'s overrides query doesn't
        # block on a real DB connection in unit-test environments.
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "1",
    }
    try:
        with patch.dict(os.environ, env, clear=False):
            with patch("mem0.Memory.from_config", return_value=MagicMock()):
                import main as server_main
                importlib.reload(server_main)
                yield server_main
    finally:
        sys.path.remove(str(SERVER_DIR))


class TestHasEntityScopeTopLevel:
    def test_user_id_present_returns_true(self, main_module):
        from main import MemoryCreate, _has_entity_scope_top_level
        req = MemoryCreate(messages=[{"role": "user", "content": "hi"}], user_id="alice")
        assert _has_entity_scope_top_level(req) is True

    def test_no_entity_returns_false(self, main_module):
        from main import MemoryCreate, _has_entity_scope_top_level
        req = MemoryCreate(messages=[{"role": "user", "content": "hi"}])
        assert _has_entity_scope_top_level(req) is False


class TestRequireEntityScope:
    def test_flat_user_id_passes(self, main_module):
        from main import _require_entity_scope
        _require_entity_scope({"user_id": "alice"})

    def test_nested_and_user_id_passes(self, main_module):
        from main import _require_entity_scope
        _require_entity_scope({"AND": [{"user_id": "alice"}, {"category": "food"}]})

    def test_empty_filters_raises_400(self, main_module):
        from fastapi import HTTPException
        from main import _require_entity_scope
        with pytest.raises(HTTPException) as exc:
            _require_entity_scope({})
        assert exc.value.status_code == 400

    def test_no_entity_in_nested_raises_400(self, main_module):
        from fastapi import HTTPException
        from main import _require_entity_scope
        with pytest.raises(HTTPException) as exc:
            _require_entity_scope({"category": "food"})
        assert exc.value.status_code == 400


class TestBuildPageUrl:
    def test_builds_absolute_url(self, main_module):
        from fastapi import Request
        from main import _build_page_url

        scope = {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "path": "/v3/memories/",
            "query_string": b"page=1&page_size=50",
            "headers": [(b"host", b"localhost:8888")],
            "server": ("localhost", 8888),
        }
        req = Request(scope=scope)
        url = _build_page_url(req, page=2, page_size=50)
        assert url == "http://localhost:8888/v3/memories/?page=2&page_size=50"
