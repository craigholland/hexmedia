from __future__ import annotations

from typing import Generator
from fastapi import Depends

from hexmedia.common.settings import get_settings, Settings
from hexmedia.database.core.main import get_session
from sqlalchemy.orm import Session

def get_settings_dep() -> Settings:
    return get_settings()

def get_db(session_gen: Generator = Depends(get_session)) -> Session:
    # get_session() yields a Session and handles commit/rollback in its own try/finally
    return session_gen  # FastAPI resolves generator dependency correctly
