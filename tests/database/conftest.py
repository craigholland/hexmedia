# tests/database/conftest.py
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

APP_SCHEMA = "hexmedia"

@pytest.fixture()
def db(db_engine) -> Session:
    """
    Per-test SQLAlchemy Session bound to a transaction (rolled back after each test).
    Uses the engine provided by the top-level conftest.
    """
    connection = db_engine.connect()
    trans = connection.begin()

    # Ensure the right search_path for this connection
    connection.execute(text(f'SET search_path TO "{APP_SCHEMA}", public'))

    session = Session(bind=connection, future=True)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
