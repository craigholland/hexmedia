from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from hexmedia.common.settings import get_settings
from hexmedia.services.ingest.utils import is_supported_media_file
from hexmedia.services.ingest.worker import IngestWorker
from hexmedia.domain.dataclasses.reports import IngestReport


class IngestService:
    """
    High-level orchestrator that finds candidate files and delegates to IngestWorker.
    """

    def __init__(self, db: Session):
        self.db = db
        self.cfg = get_settings()

    def scan_incoming(self, *, limit: Optional[int] = None) -> List[Path]:
        """
        Return supported files found directly under the configured incoming_root.
        (Non-recursive for now; we can add recursion/globbing later if needed.)
        """
        root: Path = self.cfg.incoming_root
        if not root.exists():
            return []
        files = [p for p in root.iterdir() if p.is_file() and is_supported_media_file(p)]
        maxn = limit if limit is not None else self.cfg.ingest_run_limit
        return files[:maxn]

    def plan(self, files: Iterable[Path | str] | None = None, *, limit: Optional[int] = None) -> List[dict]:
        """
        Return the planner items (list[dict]) without moving or DB writes.
        """
        if files:
            norm: List[Path] = [Path(f) for f in files]
        else:
            norm = self.scan_incoming(limit=limit)
            # cap to limit if caller passed explicit files
        maxn = limit if limit is not None else self.cfg.ingest_run_limit
        norm = norm[:maxn]
        # reuse worker dry-run to get planned_items
        rpt = self.run(files=norm, dry_run=True, limit=maxn)
        return rpt.planned_items or []

    def run(
        self,
        files: Iterable[Path | str] | None = None,
        *,
        dry_run: bool = False,
        limit: Optional[int] = None,
    ) -> IngestReport:
        if files:
            norm_files: List[Path] = [Path(f) for f in files]
        else:
            norm_files = self.scan_incoming(limit=limit)
        # cap to limit if caller passed explicit files
        maxn = limit if limit is not None else self.cfg.ingest_run_limit
        norm_files = norm_files[:maxn]

        worker = IngestWorker(self.db)
        return worker.run(norm_files, dry_run=dry_run)
