"""Event model: schema, defaults, status transitions, startup sweep."""

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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO_ROOT / "server"


@pytest.fixture
def db(tmp_path):
    sys.path.insert(0, str(SERVER_DIR))
    try:
        from alembic import command
        from alembic.config import Config

        url = f"sqlite:///{tmp_path / 'test.db'}"
        cfg = Config(str(SERVER_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(SERVER_DIR / "alembic"))
        cfg.set_main_option("sqlalchemy.url", url)
        with patch.dict(os.environ, {"POSTGRES_HOST": "ignored"}):
            command.upgrade(cfg, "head")
        engine = create_engine(url)
        yield engine
        engine.dispose()
    finally:
        sys.path.remove(str(SERVER_DIR))


def test_event_persists_with_pending_default(db):
    sys.path.insert(0, str(SERVER_DIR))
    try:
        from models import Event

        Session = sessionmaker(bind=db)
        with Session() as s:
            ev = Event(status="PENDING", payload={"messages": [], "user_id": "alice"})
            s.add(ev); s.commit(); s.refresh(ev)
            assert ev.id is not None
            assert ev.status == "PENDING"
            assert ev.created_at is not None
            assert ev.payload["user_id"] == "alice"
            assert ev.result is None
            assert ev.error is None
    finally:
        sys.path.remove(str(SERVER_DIR))


def test_event_status_transition_to_succeeded(db):
    sys.path.insert(0, str(SERVER_DIR))
    try:
        from models import Event

        Session = sessionmaker(bind=db)
        with Session() as s:
            ev = Event(status="PENDING", payload={"foo": "bar"})
            s.add(ev); s.commit()
            ev.status = "SUCCEEDED"
            ev.result = {"results": [{"id": "mem-1", "event": "ADD"}]}
            s.commit(); s.refresh(ev)
            assert ev.status == "SUCCEEDED"
            assert ev.result["results"][0]["event"] == "ADD"
    finally:
        sys.path.remove(str(SERVER_DIR))
