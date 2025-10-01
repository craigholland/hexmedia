# services/api/routers/ingest.py
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from hexmedia.common.settings import get_settings
from hexmedia.services.api.deps import transactional_session, get_db
from hexmedia.services.schemas.ingest import (
    IngestRunRequest,
    IngestRunResponse,
    IngestPlanItemSchema,
)
from hexmedia.services.ingest.service import IngestService

logger = logging.getLogger(__name__)
router = APIRouter()

# --- DB dependency ------------------------------------------------------------

#_cfg = get_settings()
#_engine = create_engine(_cfg.database_url, future=True, pool_pre_ping=True)
#_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
#
#
# def get_db() -> Iterable[Session]:
#     """FastAPI dependency that yields a SQLAlchemy Session."""
#     db = _SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# --- Helpers -----------------------------------------------------------------

def _coerce_files(req: IngestRunRequest) -> Optional[List[Path]]:
    """
    Convert request.files to Paths if provided.
    If None (not provided), return None and let the service auto-scan incoming_root.
    """
    if req.files is None:
        return None
    paths: List[Path] = []
    for s in req.files:
        try:
            paths.append(Path(s))
        except Exception as ex:  # defensive
            logger.warning("Skipping invalid file path %r: %s", s, ex)
    return paths


def _report_to_response(report) -> IngestRunResponse:
    """
    Map service/domain report object into the API response model.
    Assumes the report has: started_at, finished_at, error_details, items, planned_items.
    """
    if report is None:
        now = datetime.now(timezone.utc)
        return IngestRunResponse(
            ok=False,
            started_at=now,
            finished_at=now,
            error_details=["ingest returned no report"],
            items=[],
            planned_items=None,
        )

    planned: Optional[List[IngestPlanItemSchema]] = None
    if getattr(report, "planned_items", None):
        planned = []
        for it in report.planned_items:
            try:
                if hasattr(it, "model_dump"):
                    data = it.model_dump()
                elif isinstance(it, dict):
                    data = it
                else:
                    data = {
                        "src": str(getattr(it, "src", "")),
                        "media_folder": getattr(it, "media_folder", ""),
                        "identity_name": getattr(it, "identity_name", ""),
                        "ext": getattr(it, "ext", ""),
                        "dest_rel_dir": getattr(it, "dest_rel_dir", ""),
                        "dest_filename": getattr(it, "dest_filename", ""),
                        "bucket": getattr(it, "bucket", ""),
                        "item": getattr(it, "item", ""),
                        "kind": getattr(it, "kind", "unknown"),
                        "supported": bool(getattr(it, "supported", False)),
                    }
                planned.append(IngestPlanItemSchema(**data))
            except Exception as ex:
                logger.exception("Failed to coerce planned item %r: %s", it, ex)

    ok = len(getattr(report, "error_details", []) or []) == 0

    # started_at/finished_at should be datetime already; just pass through
    return IngestRunResponse(
        ok=ok,
        started_at=getattr(report, "started_at"),
        finished_at=getattr(report, "finished_at"),
        error_details=list(getattr(report, "error_details", []) or []),
        items=list(getattr(report, "items", []) or []),
        planned_items=planned,
    )


# --- Routes ------------------------------------------------------------------

@router.post(
    "/plan",
    response_model=IngestRunResponse,
    summary="Build an ingest plan",
)
def plan_ingest(req: IngestRunRequest, session: Session = Depends(get_db)) -> IngestRunResponse:
    """
    Returns a planning-only view of what the ingest *would* do.
    Ignores any `dry_run=false` in the payload; this endpoint is always a dry-run.
    - If `req.files` is provided: plan for exactly those files.
    - Otherwise: service will auto-scan the configured `incoming_root`.
    """
    try:
        svc = IngestService(db=session)
        files = _coerce_files(req)
        report = svc.run(files, dry_run=True)
        return _report_to_response(report)
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception("Planning failed: %s", ex)
        raise HTTPException(status_code=500, detail=f"Planning failed: {ex}")


@router.post(
    "/run",
    response_model=IngestRunResponse,
    summary="Run ingest",
)
def run_ingest(req: IngestRunRequest, session: Session = Depends(transactional_session)) -> IngestRunResponse:
    """
    Execute a single ingest pass.

    - If `req.files` is provided: ingest exactly those files.
    - Otherwise: service will auto-scan the configured `incoming_root`.
    - If `dry_run` is true in the payload: this will behave like planning but
      remains a separate endpoint for operators who always call `/run`.
    """
    try:
        svc = IngestService(db=session)
        files = _coerce_files(req)
        report = svc.run(files)
        return _report_to_response(report)
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception("Ingest failed: %s", ex)
        raise HTTPException(status_code=500, detail=f"Ingest failed: {ex}")
