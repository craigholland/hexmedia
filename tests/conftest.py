# tests/conftest.py
from __future__ import annotations
import os
import time
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from testcontainers.postgres import PostgresContainer

from hexmedia.database.models import Base  # <-- imports your models/metadata

APP_SCHEMA = "hexmedia"

@pytest.fixture(scope="session")
def _postgres_container():
    # Use psycopg (v3) driver in URL
    with PostgresContainer("postgres:15-alpine") as pg:
        # Force psycopg driver in the URL returned by testcontainers (it defaults to psycopg2)
        url = pg.get_connection_url().replace("psycopg2", "psycopg")
        yield url

def _prepare_schema(engine: Engine, schema: str = APP_SCHEMA) -> None:
    with engine.begin() as conn:
        conn.execute(text(f'create schema if not exists "{schema}"'))
        conn.execute(text(f'set search_path to "{schema}", public'))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

@pytest.fixture(scope="session")
def db_engine(_postgres_container) -> Engine:
    engine = create_engine(_postgres_container, future=True)
    _prepare_schema(engine, APP_SCHEMA)

    # 🚫 Skip Alembic here; just create tables from models
    Base.metadata.create_all(bind=engine)

    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)

@pytest.fixture()
def db(db_engine) -> Engine:
    return db_engine
