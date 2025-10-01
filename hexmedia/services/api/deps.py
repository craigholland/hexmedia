# hexmedia/services/api/deps.py
from __future__ import annotations
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from hexmedia.database.core.main import SessionLocal
from hexmedia.domain.ports.probe import MediaProbePort
from hexmedia.services.probe.ffprobe_adapter import FFprobeAdapter  # note the lowercase 'p' in your codebase

def get_media_probe() -> MediaProbePort:
    """
    Provide a MediaProbePort implementation (ffprobe) via DI.
    Swappable later if you add other probers.
    """
    return FFprobeAdapter()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def transactional_session(db: Session = Depends(get_db)) -> Generator[Session, None, None]:
    """
    Request-scoped transaction. Any repo/service using this session
    participates in the same transaction.

    Usage in routers:
      def endpoint(session: Session = Depends(transactional_session)):
          ...
    """
    # Using the Session.begin() context ensures COMMIT on normal exit,
    # and ROLLBACK if an exception bubbles out.
    with db.begin():
        yield db
