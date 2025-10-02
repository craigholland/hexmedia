# hexmedia/services/api/routers/ingest.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal

from hexmedia.services.api.deps import transactional_session, get_media_probe
from hexmedia.domain.ports.probe import MediaProbePort

from hexmedia.services.schemas.ingest import (
    IngestPlanItemSchema,
    IngestRunRequest,
    IngestRunResponse,
)
from hexmedia.services.mappers.ingest import (
    to_plan_items_schemas,
    to_run_response_from_report,
)

from hexmedia.services.ingest.service import IngestService
from hexmedia.common.settings import get_settings
from hexmedia.services.schemas.thumbs import ThumbRequest, ThumbResponse, ThumbPlanItem
from hexmedia.services.ingest.thumb_service import ThumbService
from hexmedia.database.repos.media_query import MediaQueryRepo


cfg = get_settings()
router = APIRouter(prefix=f"{cfg.api.prefix}/ingest", tags=["ingest"])

@router.post("/plan", response_model=list[IngestPlanItemSchema])
def plan_ingest(
    limit: int | None = Query(None, ge=1, le=1000, description="Max files to plan this call"),
    session: Session = Depends(transactional_session),
) -> list[IngestPlanItemSchema]:
    svc = IngestService(db=session)
    if limit is None:
        limit = cfg.ingest_run_limit
    planned = svc.plan(limit=limit)
    return to_plan_items_schemas(planned)


@router.post("/run", response_model=IngestRunResponse)
def run_ingest(
    payload: IngestRunRequest,
    limit: int | None = Query(None, ge=1, le=1000, description="Max files to ingest this call"),
    session: Session = Depends(transactional_session),
    probe: MediaProbePort = Depends(get_media_probe),  # reserved for future DI
) -> IngestRunResponse:
    svc = IngestService(db=session)
    if limit is None:
        limit = cfg.ingest_run_limit
    report = svc.run(files=payload.files, dry_run=False, limit=limit)
    planned_schemas = to_plan_items_schemas(report.planned_items or []) if report.planned_items else None
    return to_run_response_from_report(report=report, planned_items=planned_schemas)


@router.post("/thumb", response_model=ThumbResponse)
def generate_thumbs(
    req: ThumbRequest,
    session: Session = Depends(transactional_session),
) -> ThumbResponse:
    settings = get_settings()
    workers = req.workers if req.workers is not None else 1
    workers = max(1, min(workers, settings.max_thumb_workers))

    svc = ThumbService(session)
    rep = svc.run(
        limit=req.limit,
        workers=workers,
        regenerate=req.regenerate,
        include_missing=req.include_missing,
        thumb_format=req.thumb_format or settings.thumb_format,
        collage_format=(req.collage_format or req.thumb_format or settings.collage_format),
        thumb_width=req.thumb_width or settings.thumb_width,
        tile_width=req.tile_width or settings.collage_tile_width,
        upscale_policy=req.upscale_policy or settings.upscale_policy,
    )
    return ThumbResponse(
        started_at=rep.started_at,
        finished_at=rep.finished_at,
        scanned=rep.scanned,
        generated=rep.generated,
        updated=rep.updated,
        skipped=rep.skipped,
        errors=rep.errors,
        error_details=rep.error_details,
    )

@router.get("/thumb_plan", response_model=list[ThumbPlanItem])
def thumb_plan(
    limit: int | None = Query(None, ge=1, le=100),
    missing: Literal["either", "both"] = Query(
        "either", description="List videos missing either asset (default) or both"
    ),
    session: Session = Depends(transactional_session),
) -> list[ThumbPlanItem]:
    if limit is None:
        limit = cfg.ingest_run_limit

    q = MediaQueryRepo(session)
    tuples = q.find_video_candidates_for_thumbs(
        limit=limit,
        regenerate=False,
        missing=missing,   # <— direct passthrough
    )
    return [
        ThumbPlanItem(media_item_id=mid, rel_dir=rel_dir, file_name=file_name)
        for (mid, rel_dir, file_name) in tuples
    ]