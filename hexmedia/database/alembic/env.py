# hexmedia/database/alembic/env.py
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Connection

# --- Load app settings --------------------------------------------------------
# This import must work without importing the whole app graph (keep it light).
from hexmedia.common.settings import get_settings

cfg = get_settings()

# --- Alembic Config -----------------------------------------------------------
alembic_config = context.config

# If alembic.ini has a loggers section, set it up.
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Allow overriding via env var if desired; otherwise use Settings.
database_url = os.getenv("DATABASE_URL", cfg.database_url)

# If you have a Base.metadata, import it here so autogenerate can detect models.
# Keep this import *minimal* to avoid importing the entire app.
try:
    from hexmedia.database.core.main import Base  # your declarative base
    target_metadata = Base.metadata
except Exception:
    # Fallback: no metadata (migrations won't autogenerate diffs)
    target_metadata = None

# Optional: constrain autogenerate to only your app schema.
# This is a gentle filter; your migrations can still target any schema explicitly.
include_schemas = True
version_table_schema = getattr(cfg, "alembic_version_table_schema", "public")


def include_object(object, name, type_, reflected, compare_to):
    """Limit autogenerate to our schema (but still allow version table in public)."""
    obj_schema = getattr(object, "schema", None)
    if type_ == "table":
        if obj_schema is None:
            # tables created without explicit schema are treated as in search_path;
            # allow them (common when using SET search_path)
            return True
        if obj_schema in {cfg.db_schema, version_table_schema}:
            return True
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection)."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=include_schemas,
        include_object=include_object,
        version_table_schema=version_table_schema,
    )

    with context.begin_transaction():
        context.run_migrations()


def _prepare_connection(conn: Connection) -> None:
    """
    Ensure schema exists, set search_path, and create useful extensions.
    This keeps migrations simpler and consistent across dev/CI.
    """
    # Create our application schema if missing
    conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{cfg.db_schema}"'))
    # Keep public first for extensions, then our app schema in search_path
    conn.execute(text(f"SET search_path TO {cfg.db_schema}, public"))

    # Make UUID / crypto helpers available (idempotent)
    # Use whichever your models/migrations rely on.
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))  # supports uuid_generate_v4()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with an Engine/Connection)."""
    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        _prepare_connection(connection)

        # NOTE: If your models set Base.metadata.schema = cfg.db_schema
        # autogenerate will emit schema-qualified DDL automatically.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=include_schemas,
            include_object=include_object,
            version_table_schema=version_table_schema,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=False,  # set True for SQLite batch mode, not needed on Postgres
        )

        with context.begin_transaction():
            context.run_migrations()


# Entrypoint selected by Alembic
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
