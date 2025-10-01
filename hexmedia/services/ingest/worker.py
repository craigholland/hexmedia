# hexmedia/services/ingest/worker.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Callable, Any

from sqlalchemy.orm import Session

from hexmedia.common.settings import get_settings
from hexmedia.database.repos.media_repo import SqlAlchemyMediaRepo
from hexmedia.domain.dataclasses.reports import IngestReport
from hexmedia.domain.entities.media_item import MediaItem, MediaIdentity
from hexmedia.domain.policies.ingest_planner import IngestPlanner
from hexmedia.domain.ports.probe import MediaProbePort
from hexmedia.services.filesystem.paths import ensure_item_dir, move_into_item_dir
from hexmedia.services.ingest.utils import is_supported_media_file, sha256_of_file
from hexmedia.services.probe.ffprobe_adapter import FFprobeAdapter  # <-- default adapter
from hexmedia.common.logging import get_logger

logger = get_logger()

class IngestWorker:
    """
    Executes the plan: move files into place, create DB rows, enrich with probe data.
    """

    def __init__(
        self,
        db: Session,
        *,
        planner: Optional[IngestPlanner] = None,
        repo: Optional[SqlAlchemyMediaRepo] = None,
        prober: Optional[Callable[[], MediaProbePort]] = None,
    ) -> None:
        self.db = db
        self.cfg = get_settings()

        self.repo: SqlAlchemyMediaRepo = repo or SqlAlchemyMediaRepo(db)
        self.planner = planner or IngestPlanner(query_repo=self.repo)
        # prober is a factory returning a MediaProbePort instance (e.g., lambda: FFprobeAdapter())
        self.prober: Callable[[], MediaProbePort] = prober or (lambda: FFprobeAdapter())

    def run(self, files: Iterable[Path] | None, *, dry_run: bool = False) -> IngestReport:
        rpt = IngestReport()
        rpt.start()

        file_list: List[Path] = list(files or [])
        if not file_list:
            rpt.stop()
            return rpt

        plan = self.planner.plan(file_list)
        rpt.planned_items = plan

        if dry_run:
            rpt.stop()
            return rpt

        media_root = self.cfg.media_root

        for item in plan:
            if not item.get("supported"):
                continue

            src = Path(item["src"])
            bucket = item["bucket"]
            identity = item["item"]
            ext = item["ext"]
            kind = item["kind"]

            # Build the media identity (domain)
            midentity = MediaIdentity(
                media_folder=bucket,
                identity_name=identity,
                video_ext=ext
            )

            # -------------------------
            # 1) Probe on the SOURCE file
            # -------------------------
            try:
                probe_res = self.prober().probe(src)
            except Exception as ex:
                rpt.add_error(f"IngestWorker: probe failed for {src}: {ex}")
                # All-or-nothing: leave file in incoming, skip DB and move
                continue

            # -------------------------
            # 2) Compute size/hash on SOURCE (idempotent; file not moved yet)
            # -------------------------
            try:
                size_bytes = src.stat().st_size
                sha256 = sha256_of_file(src)
            except Exception as ex:
                rpt.add_error(f"IngestWorker: hashing/stat failed for {src}: {ex}")
                # All-or-nothing: leave file in incoming
                continue

            # Prepare a domain entity populated with probe info
            mi = MediaItem(
                kind=kind,
                identity=midentity,
                size_bytes=size_bytes,
                hash_sha256=sha256,
            )
            # Enrich from probe
            mi.duration_sec = probe_res.duration_sec
            mi.width = probe_res.width
            mi.height = probe_res.height
            mi.fps = probe_res.fps
            mi.bitrate = probe_res.bitrate
            mi.codec_video = probe_res.codec_video
            mi.codec_audio = probe_res.codec_audio
            mi.container = probe_res.container
            mi.aspect_ratio = probe_res.aspect_ratio
            mi.language = probe_res.language
            mi.has_subtitles = probe_res.has_subtitles

            # -------------------------
            # 3) DB INSERT + 4) MOVE (inside a SAVEPOINT)
            # -------------------------
            # Rationale:
            #  - Insert the DB row, flush to allocate id and detect uniqueness violations.
            #  - Only after DB insert succeeds, perform the filesystem move.
            #  - If MOVE fails, rollback the savepoint so no DB row is left behind.
            try:
                from sqlalchemy.exc import SQLAlchemyError  # local import to avoid top-level dependency elsewhere
                with self.db.begin_nested():  # SAVEPOINT for this item only
                    # 3) insert (no commit here; transactional_session handles outer commit)
                    self.repo.create_media_item(mi)  # repo should only add/flush/refresh

                    # 4) move last (if this fails, we roll back the savepoint)
                    item_dir = ensure_item_dir(media_root, bucket, identity)
                    dest_path = move_into_item_dir(src, item_dir, identity, ext)

                # If we get here, both DB insert and move succeeded for this item
                rpt.created += 1
                rpt.moved += 1

            except Exception as ex:
                # Roll back this item’s DB changes (savepoint)
                try:
                    self.db.rollback()  # rolls back to the nearest savepoint if inside begin_nested
                except Exception:
                    # even if rollback raises, we still record the error
                    pass
                rpt.add_error(f"IngestWorker: db+move transactional unit failed for {src}: {ex}")
                # File remains in incoming since move is last and failed before renaming,
                # or DB insertion is rolled back if failure occurred after insertion.
                continue

        rpt.stop()
        return rpt
