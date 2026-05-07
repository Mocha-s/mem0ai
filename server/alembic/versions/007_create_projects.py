"""Create projects table and seed the default project

Revision ID: 007
Revises: 006
Create Date: 2026-05-07

The OSS server is single-tenant single-admin today. We introduce a Project
abstraction with a single seeded row (``is_default=true``) so that platform-aligned
project-scoped fields (``retrieval_criteria``, ``custom_instructions``,
``custom_categories``, ``multilingual``, ``decay``) have a clean, typed home —
separate from the LLM/vector/embedder global config. The schema is multi-row from
day one so future multi-project support does not require another migration.

This migration also lifts any of those five fields that are currently stored
inside ``Settings.config_overrides`` JSON (silently passed through in earlier
versions) into the new ``projects`` row, then strips them from the JSON to
prevent ambiguous re-merge at boot.
"""

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PROJECT_FIELDS = (
    "custom_instructions",
    "custom_categories",
    "retrieval_criteria",
    "multilingual",
    "decay",
)


def _json_type():
    return JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("custom_instructions", sa.Text(), nullable=True),
        sa.Column("custom_categories", _json_type(), nullable=True),
        sa.Column("retrieval_criteria", _json_type(), nullable=True),
        sa.Column("multilingual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("decay", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # Partial unique index: at most one default project. Postgres supports
    # partial indexes; on SQLite we fall back to a regular unique index on a
    # generated column-equivalent — for the OSS test path we simply enforce
    # uniqueness in the seed insert below.
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX ix_projects_one_default ON projects (is_default) "
            "WHERE is_default"
        )

    # Lift the five project-scoped fields out of Settings.config_overrides if
    # an earlier deployment stored them there.
    lifted: dict = {}
    settings_row = bind.execute(
        sa.text("SELECT value FROM settings WHERE key = 'config_overrides'")
    ).first()
    if settings_row and settings_row[0]:
        try:
            overrides = json.loads(settings_row[0])
        except (TypeError, ValueError):
            overrides = {}
        if isinstance(overrides, dict):
            for field in _PROJECT_FIELDS:
                if field in overrides:
                    lifted[field] = overrides.pop(field)
            if lifted:
                bind.execute(
                    sa.text(
                        "UPDATE settings SET value = :value, updated_at = now() "
                        "WHERE key = 'config_overrides'"
                    ),
                    {"value": json.dumps(overrides)},
                )

    project_id = uuid.uuid4()
    insert_payload = {
        "id": project_id,
        "name": "default",
        "is_default": True,
        "custom_instructions": lifted.get("custom_instructions"),
        "custom_categories": lifted.get("custom_categories"),
        "retrieval_criteria": lifted.get("retrieval_criteria"),
        "multilingual": bool(lifted.get("multilingual", False)),
        "decay": bool(lifted.get("decay", False)),
    }

    # JSON columns require driver-level encoding; pass dicts/lists directly on
    # PG (psycopg handles them) and JSON-encode on SQLite (where the variant
    # falls back to TEXT).
    if bind.dialect.name == "sqlite":
        for field in ("custom_categories", "retrieval_criteria"):
            value = insert_payload[field]
            if value is not None:
                insert_payload[field] = json.dumps(value)

    op.execute(
        sa.text(
            "INSERT INTO projects "
            "(id, name, is_default, custom_instructions, custom_categories, "
            "retrieval_criteria, multilingual, decay) VALUES "
            "(:id, :name, :is_default, :custom_instructions, :custom_categories, "
            ":retrieval_criteria, :multilingual, :decay)"
        ).bindparams(**insert_payload)
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Re-merge the default project's fields back into Settings.config_overrides
    # so a downgrade does not lose them.
    row = bind.execute(
        sa.text(
            "SELECT custom_instructions, custom_categories, retrieval_criteria, "
            "multilingual, decay FROM projects WHERE is_default"
        )
    ).first()
    if row:
        merged = {
            "custom_instructions": row[0],
            "custom_categories": row[1],
            "retrieval_criteria": row[2],
            "multilingual": bool(row[3]),
            "decay": bool(row[4]),
        }
        # Drop None entries; bool fields default False so don't clutter overrides
        merged = {k: v for k, v in merged.items() if v not in (None, False)}

        existing_row = bind.execute(
            sa.text("SELECT value FROM settings WHERE key = 'config_overrides'")
        ).first()
        if existing_row and existing_row[0]:
            try:
                overrides = json.loads(existing_row[0])
            except (TypeError, ValueError):
                overrides = {}
            if not isinstance(overrides, dict):
                overrides = {}
            overrides.update(merged)
            bind.execute(
                sa.text(
                    "UPDATE settings SET value = :value, updated_at = now() "
                    "WHERE key = 'config_overrides'"
                ),
                {"value": json.dumps(overrides)},
            )
        elif merged:
            bind.execute(
                sa.text(
                    "INSERT INTO settings (key, value, updated_at) "
                    "VALUES ('config_overrides', :value, now())"
                ),
                {"value": json.dumps(merged)},
            )

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_projects_one_default")
    op.drop_table("projects")
