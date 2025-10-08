# tests/services/conftest.py
from __future__ import annotations
import pytest
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import text
from starlette.testclient import TestClient

from hexmedia.services.api.app import create_app
from hexmedia.services.api.deps import transactional_session

APP_SCHEMA = "hexmedia"

@pytest.fixture()
def api_client(db_engine):
    """
    A TestClient whose FastAPI dependency `transactional_session` is overridden
    to yield a single SQLAlchemy Session bound to the test engine/transaction.
    All API calls in one test share the same session (so POST -> GET works),
    and everything is rolled back at the end of the test.
    """
    # Build one connection/transaction for the whole test
    conn = db_engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, future=True)
    session.execute(text(f'SET search_path TO "{APP_SCHEMA}", public'))

    # Create the app and override the dependency to yield THIS session
    app = create_app()

    def _override():
        # yield the same session for every request in this test
        yield session

    app.dependency_overrides[transactional_session] = _override

    try:
        with TestClient(app) as client:
            yield client
    finally:
        # Cleanup
        app.dependency_overrides.clear()
        session.close()
        trans.rollback()
        conn.close()