from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from db import Base, _build_database_url

# Import models so Base.metadata picks up all tables
import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from alembic.ini with the runtime database URL.
# Only override when the URL is the placeholder from alembic.ini — this lets
# callers (notably pytest fixtures) override the URL programmatically via
# ``cfg.set_main_option("sqlalchemy.url", "sqlite:///...")`` before invoking
# ``command.upgrade(cfg, ...)``.
_INI_PLACEHOLDER_URL = "postgresql+psycopg://postgres:postgres@postgres:5432/mem0_app"
_current_url = config.get_main_option("sqlalchemy.url")
if not _current_url or _current_url == _INI_PLACEHOLDER_URL:
    config.set_main_option("sqlalchemy.url", _build_database_url())


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
