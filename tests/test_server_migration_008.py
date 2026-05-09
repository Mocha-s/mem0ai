"""Migration 008: create events table; downgrade drops it."""

from __future__ import annotations
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
pytest.importorskip("alembic", reason="alembic not installed")

from sqlalchemy import create_engine, inspect

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO_ROOT / "server"


def _alembic_cfg(url: str):
    sys.path.insert(0, str(SERVER_DIR))
    from alembic.config import Config
    cfg = Config(str(SERVER_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_creates_events_table(tmp_path):
    from alembic import command
    url = f"sqlite:///{tmp_path / 'test.db'}"
    cfg = _alembic_cfg(url)
    with patch.dict(os.environ, {"POSTGRES_HOST": "ignored"}):
        command.upgrade(cfg, "head")
    sys.path.remove(str(SERVER_DIR))

    engine = create_engine(url)
    insp = inspect(engine)
    assert "events" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("events")}
    assert {"id", "status", "payload", "result", "error", "created_at", "updated_at"} <= cols


def test_downgrade_drops_events_table(tmp_path):
    from alembic import command
    url = f"sqlite:///{tmp_path / 'test.db'}"
    cfg = _alembic_cfg(url)
    with patch.dict(os.environ, {"POSTGRES_HOST": "ignored"}):
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "-1")
    sys.path.remove(str(SERVER_DIR))

    engine = create_engine(url)
    insp = inspect(engine)
    assert "events" not in insp.get_table_names()
