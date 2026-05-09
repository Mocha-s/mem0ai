"""Create events table for async add tracking

Revision ID: 008
Revises: 007
Create Date: 2026-05-07

POST /v3/memories/add/ persists a row with status=PENDING; the BackgroundTask
worker flips it to SUCCEEDED or FAILED. GET /v1/event/{id}/ reads this table.
Partial index on (status) WHERE status='PENDING' keeps the startup sweep cheap
even when the table grows. SQLite skips the partial index (no support).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", _json_type(), nullable=False),
        sa.Column("result", _json_type(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_created_at", "events", ["created_at"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_index(
            "ix_events_pending",
            "events",
            ["status"],
            postgresql_where=sa.text("status = 'PENDING'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("ix_events_pending", table_name="events")
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_index("ix_events_status", table_name="events")
    op.drop_table("events")
