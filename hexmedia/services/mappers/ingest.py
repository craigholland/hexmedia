# hexmedia/services/mappers/ingest.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Mapping, Any, Optional

from hexmedia.services.schemas.ingest import (
    IngestPlanItemSchema,
    IngestRunResponse,
)

def _get(obj: Any, key: str, default=None):
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)

def _as_str(x: Any) -> str:
    if isinstance(x, Path):
        return str(x)
    return "" if x is None else str(x)

def to_plan_items_schemas(planned: Iterable[Mapping[str, Any]]) -> List[IngestPlanItemSchema]:
    """
    Your planner currently returns a list[dict] with keys like:
      src, bucket, item, ext, kind, supported, ...
    Map them into IngestPlanItemSchema (which also includes derived dest_* fields).
    """
    out: List[IngestPlanItemSchema] = []
    for pi in planned:
        src = _as_str(_get(pi, "src"))
        bucket = _as_str(_get(pi, "bucket"))
        identity = _as_str(_get(pi, "item"))
        ext = _as_str(_get(pi, "ext"))
        kind = _as_str(_get(pi, "kind"))
        supported = bool(_get(pi, "supported", True))

        dest_rel_dir = f"{bucket}/{identity}"
        dest_filename = f"{identity}.{ext}".strip(".")

        out.append(
            IngestPlanItemSchema(
                src=src,
                media_folder=bucket,
                identity_name=identity,
                ext=ext,
                dest_rel_dir=dest_rel_dir,
                dest_filename=dest_filename,
                bucket=bucket,
                item=identity,
                kind=kind or "unknown",
                supported=supported,
            )
        )
    return out

def to_run_response_from_report(
    *,
    report: Any,  # hexmedia.domain.dataclasses.reports.IngestReport
    planned_items: Optional[List[IngestPlanItemSchema]] = None,
) -> IngestRunResponse:
    """
    Build your wire DTO from the IngestReport dataclass.
    - Leaves per-item 'items' as dicts (your schema allows that).
    - Converts planned_items (if provided) to the IngestPlanItemSchema list.
    """
    ok = (len(report.error_details or []) == 0) and int(getattr(report, "errors", 0)) == 0
    return IngestRunResponse(
        ok=ok,
        started_at=report.started_at,
        finished_at=report.finished_at,
        error_details=list(report.error_details or []),
        items=list(getattr(report, "items", []) or []),
        planned_items=planned_items,
    )
