from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

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

    def scan_incoming(self) -> List[Path]:
        """
        Return supported files found directly under the configured incoming_root.
        (Non-recursive for now; we can add recursion/globbing later if needed.)
        """
        root: Path = self.cfg.incoming_root
        if not root.exists():
            return []
        return [p for p in root.iterdir() if p.is_file() and is_supported_media_file(p)]

    def run(
        self,
        files: Iterable[Path | str] | None = None,
        *,
        dry_run: bool = False,
    ) -> IngestReport:
        """
        If files is None/empty -> auto-scan incoming_root.
        Otherwise, normalize inputs to Path and pass through.
        """
        # Normalize and decide source list
        norm_files: List[Path] = []
        if files:
            for f in files:
                norm_files.append(Path(f))
        else:
            norm_files = self.scan_incoming()

        worker = IngestWorker(self.db)
        return worker.run(norm_files, dry_run=dry_run)
