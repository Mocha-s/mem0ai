"""pgvector list() supports offset and count_total."""

import pytest

pytest.importorskip("psycopg2", reason="psycopg2 not installed")
from psycopg2 import sql

from mem0.vector_stores.pgvector import PGVector


def _make_pg(captured: dict, count_value: int = 1):
    """Build a PGVector with a stubbed cursor whose execute calls are captured.

    The cursor returns a single fetchall row and ``(count_value,)`` from
    fetchone so we can assert on the count surfaced to the caller.
    """
    pg = PGVector.__new__(PGVector)
    pg.collection_name = "memories"
    pg._build_filter_sql = lambda f: None

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def execute(self, sql_, params):
            captured["calls"].append((str(sql_), tuple(params)))

        def fetchall(self):
            return [(b"a", None, {"data": "x"})]

        def fetchone(self):
            return (count_value,)

    pg._get_cursor = lambda: _Cursor()
    pg._col = lambda: sql.Identifier("memories")
    return pg


def test_list_offset_passes_through_to_sql(monkeypatch):
    captured = {"calls": []}
    pg = _make_pg(captured, count_value=42)

    out = pg.list(filters=None, top_k=10, offset=20, count_total=True)

    # OFFSET must appear in the list query, count(*) must appear separately
    assert any("OFFSET" in s for s, _ in captured["calls"])
    assert any("count(*)" in s for s, _ in captured["calls"])

    # Surfaced count comes through unchanged from fetchone()
    assert isinstance(out, dict)
    assert "results" in out and "count" in out
    assert out["count"] == 42

    # The list query's last two bound params must be (top_k, offset)
    list_call = next(c for c in captured["calls"] if "OFFSET" in c[0])
    assert list_call[1][-2:] == (10, 20)


def test_list_no_count_total_skips_count_query(monkeypatch):
    """count_total=False must issue exactly ONE query (no extra count(*) call)."""
    captured = {"calls": []}
    pg = _make_pg(captured)

    out = pg.list(filters=None, top_k=10, count_total=False)

    # No count(*) query is issued
    assert all("count(*)" not in s for s, _ in captured["calls"])
    # And exactly one query ran (the list query)
    assert len(captured["calls"]) == 1
    # The dict shape is preserved with count=None
    assert "count" in out and out["count"] is None
    assert "results" in out


def test_list_default_no_count_total(monkeypatch):
    """The default (no count_total kwarg) must also skip the count(*) query."""
    captured = {"calls": []}
    pg = _make_pg(captured)

    out = pg.list(filters=None, top_k=10)

    assert len(captured["calls"]) == 1
    assert all("count(*)" not in s for s, _ in captured["calls"])
    assert out["count"] is None
