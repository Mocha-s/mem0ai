"""End-to-end hybrid search via the V3 endpoint, against pgvector.

Requires Compose-up: POSTGRES_HOST set to a reachable pgvector instance.
Skipped on the default SQLite test config — set RUN_PGVECTOR_TESTS=1 to enable.
"""

import os
import pytest

pytest.importorskip("psycopg2", reason="psycopg2 not installed")

skip_no_pg = pytest.mark.skipif(
    not os.getenv("RUN_PGVECTOR_TESTS"),
    reason="set RUN_PGVECTOR_TESTS=1 to run pgvector hybrid-search test",
)


@skip_no_pg
def test_search_returns_combined_score_and_categories():
    """Real fixture (Compose pgvector + mem0 SDK) lands when the CI pgvector
    job is added. Body is a placeholder asserting the contract."""
    pytest.skip("pgvector CI fixture not implemented yet")
