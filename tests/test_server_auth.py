"""Comprehensive E2E tests for REST API server authentication (V3 routes).

Tests the actual server/main.py app through FastAPI's TestClient (full ASGI
round-trip) covering:
  - Auth disabled mode (ADMIN_API_KEY unset)
  - Auth enabled mode (ADMIN_API_KEY set)
  - Edge cases: empty keys, near-miss keys, timing-safe comparison, header
    casing, response headers, startup logging, and full CRUD flows through auth.

All routes that used to live under ``/memories`` now live under ``/v3/memories/*``.

Fixtures (``sqlite_db`` + ``_load_app_with_db``) bring up an Alembic-migrated
SQLite DB so the V3 add endpoint has a real ``events`` table to insert into.
"""

import importlib
import logging
import os
import sys
import uuid
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
def _mock_memory():
    """Patch Memory.from_config so the server imports without a real backend."""
    mock_instance = MagicMock()
    mock_instance.get.return_value = {"id": "mem-1", "memory": "test memory", "user_id": "alice"}
    mock_instance.get_all.return_value = {
        "results": [{"id": "mem-1", "memory": "test memory", "user_id": "alice"}],
        "count": 1,
    }
    mock_instance.add.return_value = {"results": [{"id": "mem-1", "event": "ADD", "memory": "test"}]}
    mock_instance.search.return_value = [{"id": "mem-1", "memory": "test", "score": 0.9}]
    mock_instance.update.return_value = {"message": "Memory updated"}
    mock_instance.history.return_value = [{"id": "mem-1", "old_memory": "a", "new_memory": "b"}]
    mock_instance.delete.return_value = None
    mock_instance.delete_all.return_value = {"message": "Memories deleted successfully!"}
    mock_instance.reset.return_value = None

    with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
        with patch("mem0.Memory.from_config", return_value=mock_instance):
            yield mock_instance


_BASE_ENV = {
    "OPENAI_API_KEY": "fake-key",
    "JWT_SECRET": "test-secret-test-secret-test-secret",
    # Tests opt into AUTH_DISABLED via env_overrides when they want auth off.
}


@pytest.fixture(autouse=True, scope="module")
def _reset_auth_module_after_tests():
    """Reset ``server.auth`` module-level constants after this file finishes.

    Tests in this module reload ``auth.py`` with various ADMIN_API_KEY /
    AUTH_DISABLED combinations. Without an explicit reset, the LAST test
    leaves auth.py with stale state (e.g. ``AUTH_DISABLED=False``,
    ``ADMIN_API_KEY="short"``), poisoning subsequent test files that reload
    ``main.py`` but not ``auth.py``. We reset to a permissive state at the
    end so other modules that happen to share this Python process see a
    benign baseline.
    """
    yield
    sys.path.insert(0, str(SERVER_DIR))
    try:
        with patch.dict(os.environ, _BASE_ENV | {"AUTH_DISABLED": "true", "ADMIN_API_KEY": ""}, clear=False):
            import auth as server_auth
            importlib.reload(server_auth)
    finally:
        sys.path.remove(str(SERVER_DIR))


def _load_app_with_db(env_overrides: dict, sqlite_url, engine):
    """Reload server/main.py with the given env + SQLite SessionLocal.

    Used by the auth tests (which need to switch ADMIN_API_KEY per-test) on
    top of an Alembic-migrated SQLite database so the V3 add endpoint can
    insert event rows. Always layers a baseline JWT_SECRET / OPENAI_API_KEY
    underneath the test's overrides; the auth import-time check in main.py
    raises if both AUTH_DISABLED and JWT_SECRET are unset.

    Reloads ``auth.py`` as well so module-level constants
    (``AUTH_DISABLED`` / ``ADMIN_API_KEY`` / ``JWT_SECRET``) pick up the
    per-test env. Without this, the first test's env permanently pins those
    constants for the whole session.
    """
    sys.path.insert(0, str(SERVER_DIR))
    SessionLocalSqlite = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    merged_env = {**_BASE_ENV, **env_overrides}
    try:
        with patch.dict(os.environ, merged_env, clear=False):
            import db as server_db

            server_db.engine = engine
            server_db.SessionLocal = SessionLocalSqlite

            import auth as server_auth
            importlib.reload(server_auth)

            import main as server_main
            importlib.reload(server_main)
            server_main.set_session_factory(SessionLocalSqlite)
            server_main.initialize_state(server_main.DEFAULT_CONFIG)
            return server_main.app
    finally:
        sys.path.remove(str(SERVER_DIR))


# ---------------------------------------------------------------------------
# Auth disabled (ADMIN_API_KEY not set)
# ---------------------------------------------------------------------------

class TestAuthDisabled:
    """All endpoints should be freely accessible when AUTH_DISABLED is set."""

    @pytest.fixture(autouse=True)
    def _setup(self, sqlite_db, _mock_memory):
        # AUTH_DISABLED=true is the explicit opt-out for local development;
        # an empty ADMIN_API_KEY alone no longer disables auth — the import
        # check in main.py requires JWT_SECRET unless AUTH_DISABLED is on.
        self.app = _load_app_with_db(
            {"ADMIN_API_KEY": "", "AUTH_DISABLED": "true"}, *sqlite_db
        )
        self.client = TestClient(self.app)
        self.mock = _mock_memory

    def test_root_redirects_to_docs(self):
        resp = self.client.get("/", follow_redirects=False)
        assert resp.status_code == 307
        assert "/docs" in resp.headers["location"]

    def test_get_memory_without_key(self):
        resp = self.client.get("/v3/memories/mem-1/")
        assert resp.status_code == 200
        assert resp.json()["id"] == "mem-1"

    def test_get_all_memories_without_key(self):
        resp = self.client.post("/v3/memories/", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 200

    def test_create_memory_without_key(self):
        resp = self.client.post("/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like pizza"}],
            "user_id": "alice",
        })
        assert resp.status_code == 200
        assert "event_id" in resp.json()

    def test_search_without_key(self):
        resp = self.client.post(
            "/v3/memories/search/", json={"query": "pizza", "filters": {"user_id": "alice"}}
        )
        assert resp.status_code == 200

    def test_update_memory_without_key(self):
        resp = self.client.put("/v3/memories/mem-1/", json={"text": "updated"})
        assert resp.status_code == 200

    def test_history_without_key(self):
        resp = self.client.get("/v3/memories/mem-1/history/")
        assert resp.status_code == 200

    def test_delete_memory_without_key(self):
        resp = self.client.delete("/v3/memories/mem-1/")
        assert resp.status_code == 200

    def test_delete_all_without_key(self):
        resp = self.client.post("/v3/memories/delete/", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 200

    def test_reset_without_key(self):
        resp = self.client.post("/reset")
        assert resp.status_code == 200

    def test_configure_without_key(self):
        self.mock.from_config = MagicMock()
        resp = self.client.post("/configure", json={"version": "v1.1"})
        assert resp.status_code == 200

    def test_supplying_key_still_works_when_auth_disabled(self):
        """A client that sends X-API-Key still has the key validated even
        when AUTH_DISABLED is on — current auth.py runs the API-key path
        before the AUTH_DISABLED short-circuit. A non-real key 401s."""
        resp = self.client.get(
            "/v3/memories/mem-1/", headers={"X-API-Key": "some-random-key"}
        )
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "method,path",
        [
            ("POST", "/configure"),
            ("POST", "/v3/memories/add/"),
            ("POST", "/v3/memories/"),
            ("GET", "/v3/memories/test-id/"),
            ("POST", "/v3/memories/search/"),
            ("PUT", "/v3/memories/test-id/"),
            ("GET", "/v3/memories/test-id/history/"),
            ("DELETE", "/v3/memories/test-id/"),
            ("POST", "/v3/memories/delete/"),
            ("POST", "/reset"),
        ],
    )
    def test_no_endpoint_returns_401_when_auth_disabled(self, method, path):
        resp = self.client.request(method, path)
        assert resp.status_code != 401, f"{method} {path} should not require auth"


# ---------------------------------------------------------------------------
# Auth enabled (ADMIN_API_KEY set)
# ---------------------------------------------------------------------------

class TestAuthEnabled:
    """All protected endpoints must enforce the API key."""

    API_KEY = "test-secret-key-12345"

    @pytest.fixture(autouse=True)
    def _setup(self, sqlite_db, _mock_memory):
        self.app = _load_app_with_db({"ADMIN_API_KEY": self.API_KEY}, *sqlite_db)
        self.client = TestClient(self.app)
        self.mock = _mock_memory

    # --- Rejection cases ---

    def test_missing_key_returns_401(self):
        resp = self.client.get("/v3/memories/mem-1/")
        assert resp.status_code == 401

    def test_missing_key_detail_mentions_header(self):
        resp = self.client.get("/v3/memories/mem-1/")
        assert "X-API-Key" in resp.json()["detail"]

    def test_wrong_key_returns_401(self):
        resp = self.client.get("/v3/memories/mem-1/", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

    def test_wrong_key_detail_says_invalid(self):
        resp = self.client.get("/v3/memories/mem-1/", headers={"X-API-Key": "wrong"})
        assert "Invalid" in resp.json()["detail"]

    def test_empty_string_key_returns_401(self):
        resp = self.client.get("/v3/memories/mem-1/", headers={"X-API-Key": ""})
        assert resp.status_code == 401

    def test_401_includes_www_authenticate_header(self):
        resp = self.client.get("/v3/memories/mem-1/")
        # The post-db8ac617 auth replies with ``Bearer``; pre-db8ac617 it
        # was ``ApiKey``. Track the current value.
        assert resp.headers.get("www-authenticate") == "Bearer"

    def test_near_miss_key_rejected(self):
        """Key that differs by one character should be rejected."""
        near_miss = self.API_KEY[:-1] + ("6" if self.API_KEY[-1] != "6" else "7")
        resp = self.client.get("/v3/memories/mem-1/", headers={"X-API-Key": near_miss})
        assert resp.status_code == 401

    def test_key_with_extra_whitespace_rejected(self):
        resp = self.client.get("/v3/memories/mem-1/", headers={"X-API-Key": f" {self.API_KEY} "})
        assert resp.status_code == 401

    def test_key_prefix_rejected(self):
        resp = self.client.get("/v3/memories/mem-1/", headers={"X-API-Key": self.API_KEY[:5]})
        assert resp.status_code == 401

    def test_key_with_different_case_rejected(self):
        resp = self.client.get("/v3/memories/mem-1/", headers={"X-API-Key": self.API_KEY.upper()})
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "method,path",
        [
            ("POST", "/configure"),
            ("POST", "/v3/memories/add/"),
            ("POST", "/v3/memories/"),
            ("GET", "/v3/memories/test-id/"),
            ("POST", "/v3/memories/search/"),
            ("PUT", "/v3/memories/test-id/"),
            ("GET", "/v3/memories/test-id/history/"),
            ("DELETE", "/v3/memories/test-id/"),
            ("POST", "/v3/memories/delete/"),
            ("POST", "/reset"),
        ],
    )
    def test_all_endpoints_reject_without_key(self, method, path):
        resp = self.client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should require auth"

    @pytest.mark.parametrize(
        "method,path",
        [
            ("POST", "/configure"),
            ("POST", "/v3/memories/add/"),
            ("POST", "/v3/memories/"),
            ("GET", "/v3/memories/test-id/"),
            ("POST", "/v3/memories/search/"),
            ("PUT", "/v3/memories/test-id/"),
            ("GET", "/v3/memories/test-id/history/"),
            ("DELETE", "/v3/memories/test-id/"),
            ("POST", "/v3/memories/delete/"),
            ("POST", "/reset"),
        ],
    )
    def test_all_endpoints_reject_wrong_key(self, method, path):
        resp = self.client.request(method, path, headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401, f"{method} {path} should reject wrong key"

    # --- Acceptance cases ---

    def test_root_does_not_require_key(self):
        resp = self.client.get("/", follow_redirects=False)
        assert resp.status_code == 307

    def _authed(self, method, path, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = self.API_KEY
        return self.client.request(method, path, headers=headers, **kwargs)

    def test_get_memory_with_key(self):
        resp = self._authed("GET", "/v3/memories/mem-1/")
        assert resp.status_code == 200
        assert resp.json()["id"] == "mem-1"

    def test_get_all_memories_with_key(self):
        resp = self._authed("POST", "/v3/memories/", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 200

    def test_create_memory_with_key(self):
        resp = self._authed("POST", "/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I like pizza"}],
            "user_id": "alice",
        })
        assert resp.status_code == 200
        # V3 add returns the async envelope, not {"results": [...]}.
        assert "event_id" in resp.json()

    def test_search_with_key(self):
        resp = self._authed(
            "POST", "/v3/memories/search/", json={"query": "pizza", "filters": {"user_id": "alice"}}
        )
        assert resp.status_code == 200

    def test_update_memory_with_key(self):
        resp = self._authed("PUT", "/v3/memories/mem-1/", json={"text": "updated"})
        assert resp.status_code == 200

    def test_history_with_key(self):
        resp = self._authed("GET", "/v3/memories/mem-1/history/")
        assert resp.status_code == 200

    def test_delete_memory_with_key(self):
        resp = self._authed("DELETE", "/v3/memories/mem-1/")
        assert resp.status_code == 200

    def test_delete_all_with_key(self):
        resp = self._authed("POST", "/v3/memories/delete/", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 200

    def test_reset_with_key(self):
        resp = self._authed("POST", "/reset")
        assert resp.status_code == 200

    def test_configure_with_key(self):
        resp = self._authed("POST", "/configure", json={"version": "v1.1"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Authorization header schemes — Token + Bearer-as-api-key
# ---------------------------------------------------------------------------

class TestAuthorizationHeaderSchemes:
    """The OSS server must accept three credential transports for an API key:

      * ``X-API-Key: <key>``                — historical OSS header.
      * ``Authorization: Token <key>``      — mem0 hosted-platform convention,
        also used by the OpenClaw plugin.
      * ``Authorization: Bearer <key>``     — common SDK mistake (clients that
        assume Bearer is universal). Falls back to API key only if JWT decode
        raises ``JWTError``; valid JWTs continue to authenticate as JWTs.
    """

    API_KEY = "admin-scheme-test-key-789"

    @pytest.fixture(autouse=True)
    def _setup(self, sqlite_db, _mock_memory):
        self.app = _load_app_with_db({"ADMIN_API_KEY": self.API_KEY}, *sqlite_db)
        self.client = TestClient(self.app)
        self.mock = _mock_memory
        self.sqlite_url, self.engine = sqlite_db

    # --- Authorization: Token <key> ---

    def test_authorization_token_with_admin_key_succeeds(self):
        resp = self.client.get(
            "/v3/memories/mem-1/",
            headers={"Authorization": f"Token {self.API_KEY}"},
        )
        assert resp.status_code == 200

    def test_authorization_token_lowercase_scheme_succeeds(self):
        """Scheme matching is case-insensitive (per RFC 7235)."""
        resp = self.client.get(
            "/v3/memories/mem-1/",
            headers={"Authorization": f"token {self.API_KEY}"},
        )
        assert resp.status_code == 200

    def test_authorization_token_with_invalid_key_returns_401(self):
        resp = self.client.get(
            "/v3/memories/mem-1/",
            headers={"Authorization": "Token not-a-real-key"},
        )
        assert resp.status_code == 401

    def test_authorization_token_empty_value_falls_through_to_401(self):
        resp = self.client.get("/v3/memories/mem-1/", headers={"Authorization": "Token "})
        assert resp.status_code == 401

    # --- Authorization: Bearer <api-key>  (JWT decode fails → fallback) ---

    def test_authorization_bearer_with_admin_key_falls_back_to_api_key(self):
        """A non-JWT in the Bearer slot should be accepted as an API key."""
        resp = self.client.get(
            "/v3/memories/mem-1/",
            headers={"Authorization": f"Bearer {self.API_KEY}"},
        )
        assert resp.status_code == 200

    def test_authorization_bearer_with_invalid_string_returns_401(self):
        """Neither a valid JWT nor a known API key — must reject."""
        resp = self.client.get(
            "/v3/memories/mem-1/",
            headers={"Authorization": "Bearer total-garbage-not-a-jwt-not-a-key"},
        )
        assert resp.status_code == 401

    # --- Authorization: Bearer <jwt>  (existing JWT path still works) ---

    def test_authorization_bearer_with_valid_jwt_succeeds(self):
        """Mint a JWT against the same secret the app uses, seed a matching
        User row, and verify the Bearer path still resolves it as a JWT
        (not as an API key)."""
        sys.path.insert(0, str(SERVER_DIR))
        try:
            import auth as server_auth
            from models import User
            # Insert via the ORM so the SQLAlchemy Uuid type handles the
            # SQLite-vs-Postgres storage conversion (SQLite stores UUIDs as
            # 32-char hex without hyphens; raw SQL with a hyphenated string
            # would silently miss the SELECT in db.get).
            user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
            SessionLocalSqlite = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)
            with SessionLocalSqlite() as session:
                session.add(User(
                    id=user_id,
                    name="JWT User",
                    email="jwt-user@example.com",
                    password_hash="x",
                    role="admin",
                ))
                session.commit()
            jwt_token = server_auth.create_access_token(str(user_id), "admin")
        finally:
            sys.path.remove(str(SERVER_DIR))

        resp = self.client.get(
            "/v3/memories/mem-1/",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Full CRUD flow through auth
# ---------------------------------------------------------------------------

class TestAuthenticatedCRUDFlow:
    """Verify a complete create -> read -> search -> update -> history -> delete
    cycle works end-to-end through the auth layer."""

    API_KEY = "flow-test-key-99"

    @pytest.fixture(autouse=True)
    def _setup(self, sqlite_db, _mock_memory):
        self.app = _load_app_with_db({"ADMIN_API_KEY": self.API_KEY}, *sqlite_db)
        self.client = TestClient(self.app)
        self.mock = _mock_memory

    def _authed(self, method, path, **kwargs):
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = self.API_KEY
        return self.client.request(method, path, headers=headers, **kwargs)

    def test_full_crud_cycle(self):
        # 1. Create (async — Memory.add invoked via background task)
        resp = self._authed("POST", "/v3/memories/add/", json={
            "messages": [{"role": "user", "content": "I love fresh vegetable pizza"}],
            "user_id": "alice",
        })
        assert resp.status_code == 200
        assert "event_id" in resp.json()
        self.mock.add.assert_called_once()

        # 2. Read single
        resp = self._authed("GET", "/v3/memories/mem-1/")
        assert resp.status_code == 200
        self.mock.get.assert_called_once_with("mem-1")

        # 3. Read all (V3 paginated list — top_k=page_size, offset=0, count_total=True)
        resp = self._authed("POST", "/v3/memories/", json={"filters": {"user_id": "alice"}})
        assert resp.status_code == 200
        self.mock.get_all.assert_called_once_with(
            filters={"user_id": "alice"}, top_k=100, offset=0, count_total=True,
        )

        # 4. Search
        resp = self._authed(
            "POST", "/v3/memories/search/", json={"query": "pizza", "filters": {"user_id": "alice"}}
        )
        assert resp.status_code == 200
        self.mock.search.assert_called_once()

        # 5. Update
        resp = self._authed("PUT", "/v3/memories/mem-1/", json={"text": "updated content"})
        assert resp.status_code == 200
        self.mock.update.assert_called_once()

        # 6. History
        resp = self._authed("GET", "/v3/memories/mem-1/history/")
        assert resp.status_code == 200
        self.mock.history.assert_called_once_with(memory_id="mem-1")

        # 7. Delete single
        resp = self._authed("DELETE", "/v3/memories/mem-1/")
        assert resp.status_code == 200
        self.mock.delete.assert_called_once_with(memory_id="mem-1")

        # 8. Delete all
        resp = self._authed(
            "POST", "/v3/memories/delete/", json={"filters": {"user_id": "alice"}}
        )
        assert resp.status_code == 200
        self.mock.delete_all.assert_called_once_with(filters={"user_id": "alice"})

    def test_crud_flow_blocked_without_auth(self):
        """Same flow should fail at every step without the key."""
        endpoints = [
            ("POST", "/v3/memories/add/", {"json": {
                "messages": [{"role": "user", "content": "test"}], "user_id": "alice"
            }}),
            ("GET", "/v3/memories/mem-1/", {}),
            ("POST", "/v3/memories/", {"json": {"filters": {"user_id": "alice"}}}),
            ("POST", "/v3/memories/search/", {"json": {"query": "pizza", "filters": {"user_id": "alice"}}}),
            ("PUT", "/v3/memories/mem-1/", {"json": {"data": "x"}}),
            ("GET", "/v3/memories/mem-1/history/", {}),
            ("DELETE", "/v3/memories/mem-1/", {}),
            ("POST", "/v3/memories/delete/", {"json": {"filters": {"user_id": "alice"}}}),
            ("POST", "/reset", {}),
        ]
        for method, path, kwargs in endpoints:
            resp = self.client.request(method, path, **kwargs)
            assert resp.status_code == 401, f"Unauthenticated {method} {path} should be 401"
        # Verify the mocks were NOT called (auth blocked before reaching handler).
        self.mock.add.assert_not_called()
        self.mock.get.assert_not_called()
        self.mock.search.assert_not_called()
        self.mock.update.assert_not_called()
        self.mock.history.assert_not_called()
        self.mock.delete.assert_not_called()
        self.mock.delete_all.assert_not_called()
        self.mock.reset.assert_not_called()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestAuthEdgeCases:
    """Boundary conditions and unusual inputs."""

    @pytest.fixture(autouse=True)
    def _setup(self, _mock_memory):
        self.mock = _mock_memory

    def test_very_long_api_key(self, sqlite_db):
        """Server should handle a very long key without crashing."""
        long_key = "k" * 4096
        app = _load_app_with_db({"ADMIN_API_KEY": long_key}, *sqlite_db)
        client = TestClient(app)
        resp = client.get("/v3/memories/mem-1/", headers={"X-API-Key": long_key})
        assert resp.status_code == 200

    def test_special_characters_in_api_key(self, sqlite_db):
        """Keys with special ASCII characters should work."""
        special_key = "sk-!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        app = _load_app_with_db({"ADMIN_API_KEY": special_key}, *sqlite_db)
        client = TestClient(app)

        resp = client.get("/v3/memories/mem-1/", headers={"X-API-Key": special_key})
        assert resp.status_code == 200

        resp = client.get("/v3/memories/mem-1/", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

    def test_key_env_var_not_present_at_all(self, sqlite_db):
        """When ``AUTH_DISABLED=true`` and no ADMIN_API_KEY is configured,
        unauthenticated requests should be served. (Pre-db8ac617 behavior was
        "absent ADMIN_API_KEY = auth off"; the new auth requires the explicit
        AUTH_DISABLED opt-in.)"""
        env = os.environ.copy()
        env.pop("ADMIN_API_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            app = _load_app_with_db({"AUTH_DISABLED": "true"}, *sqlite_db)
        client = TestClient(app)
        resp = client.get("/v3/memories/mem-1/")
        assert resp.status_code != 401

    def test_switching_from_enabled_to_disabled(self, sqlite_db):
        """Simulates a server restart with auth toggled off via AUTH_DISABLED."""
        # First: auth enabled
        app1 = _load_app_with_db({"ADMIN_API_KEY": "secret"}, *sqlite_db)
        c1 = TestClient(app1)
        assert c1.get("/v3/memories/mem-1/").status_code == 401

        # Then: auth disabled (via AUTH_DISABLED, the explicit opt-out)
        app2 = _load_app_with_db({"ADMIN_API_KEY": "", "AUTH_DISABLED": "true"}, *sqlite_db)
        c2 = TestClient(app2)
        assert c2.get("/v3/memories/mem-1/").status_code != 401

    def test_openapi_schema_accessible_without_key(self, sqlite_db):
        """The /docs and /openapi.json endpoints should always be reachable."""
        app = _load_app_with_db({"ADMIN_API_KEY": "secret"}, *sqlite_db)
        client = TestClient(app)

        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema

        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_schema_documents_auth(self, sqlite_db):
        """The OpenAPI schema should mention authentication."""
        app = _load_app_with_db({"ADMIN_API_KEY": "secret"}, *sqlite_db)
        client = TestClient(app)
        schema = client.get("/openapi.json").json()
        assert "Authentication" in schema.get("info", {}).get("description", "")


# ---------------------------------------------------------------------------
# Startup logging
# ---------------------------------------------------------------------------

class TestStartupLogging:
    """Verify the server emits the correct log messages at import time.

    The pre-``db8ac617`` server logged ``"UNSECURED"`` / ``"authentication
    enabled"``. The current auth system logs different messages, so these
    tests track the new strings — see ``server/main.py:78-108`` for the
    canonical set.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, _mock_memory):
        pass

    def test_warning_when_auth_disabled(self, sqlite_db, caplog):
        with caplog.at_level(logging.WARNING):
            _load_app_with_db({"ADMIN_API_KEY": "", "AUTH_DISABLED": "true"}, *sqlite_db)
        assert any("AUTH_DISABLED is enabled" in r.message for r in caplog.records)

    def test_warning_when_unconfigured(self, sqlite_db, caplog):
        """When auth is on but no admin is configured, the server warns
        the operator with a multi-line block telling them how to fix it."""
        with caplog.at_level(logging.WARNING):
            _load_app_with_db({"ADMIN_API_KEY": ""}, *sqlite_db)
        assert any(
            "no admin configured" in r.message or "Protected endpoints will return 401" in r.message
            for r in caplog.records
        )

    def test_warning_when_key_too_short(self, sqlite_db, caplog):
        with caplog.at_level(logging.WARNING):
            _load_app_with_db({"ADMIN_API_KEY": "short"}, *sqlite_db)
        assert any("shorter than" in r.message for r in caplog.records)
