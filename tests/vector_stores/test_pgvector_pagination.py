"""pgvector list() supports offset and count_total."""

import pytest

pytest.importorskip("psycopg2", reason="psycopg2 not installed")
from psycopg2 import sql

from mem0.vector_stores.pgvector import PGVector


def test_list_offset_passes_through_to_sql(monkeypatch):
    pg = PGVector.__new__(PGVector)
    pg.collection_name = "memories"
    pg._build_filter_sql = lambda f: None
    captured = {"calls": []}

    class _Cursor:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, sql_, params):
            captured["calls"].append((str(sql_), tuple(params)))
        def fetchall(self):
            return [(b"a", None, {"data": "x"})]
        def fetchone(self):
            return (1,)

    monkeypatch.setattr(pg, "_get_cursor", lambda: _Cursor())
    monkeypatch.setattr(pg, "_col", lambda: sql.Identifier("memories"))

    out = pg.list(filters=None, top_k=10, offset=20, count_total=True)

    assert any("OFFSET" in s for s, _ in captured["calls"])
    assert any("count(*)" in s for s, _ in captured["calls"])
    assert isinstance(out, dict)
    assert "results" in out and "count" in out
    assert out["count"] == 1
