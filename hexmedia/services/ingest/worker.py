# hexmedia/services/ingest/worker.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Callable

from sqlalchemy.orm import Session

from hexmedia.common.settings import get_settings
from hexmedia.database.repos.media_repo import SqlAlchemyMediaRepo
from hexmedia.domain.dataclasses.ingest import IngestPlanItem
from hexmedia.domain.dataclasses.reports import IngestReport
from hexmedia.domain.entities.media_item import MediaItem, MediaIdentity
from hexmedia.domain.policies.ingest_planner import IngestPlanner
from hexmedia.domain.ports.probe import MediaProbePort
from hexmedia.services.filesystem.paths import ensure_item_dir, move_into_item_dir
from hexmedia.services.probe.ffprobe_adapter import FFprobeAdapter  # default adapter
from hexmedia.common.logging import get_logger

logger = get_logger()


class IngestWorker:
    """
    Executes the plan: move files into place, create DB rows, enrich with probe data.
    Expects the planner to produce a list of IngestPlanItem objects.
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
            # Enforce dataclass input (no dicts)
            if not isinstance(item, IngestPlanItem):
                rpt.add_error(
                    f"IngestWorker: planner produced unsupported item type {type(item)!r}; "
                    "expected IngestPlanItem"
                )
                continue

            if not bool(item.supported):
                # Skip unsupported files silently (by design)
                continue

            # Pull required fields from the dataclass
            src = Path(item.src)
            bucket = item.bucket
            identity = item.item or getattr(item, "identity_name", None)
            ext = item.ext
            kind = item.kind

            if not identity:
                rpt.add_error(f"IngestWorker: missing identity for {src}")
                continue

            # Build the media identity (domain)
            # NOTE: In DB/FE, media_folder represents the bucket (e.g., "000"),
            # and identity_name is the 12-char slug; FE reconstructs path as
            # `${media_folder}/${identity_name}.${video_ext}`
            midentity = MediaIdentity(
                media_folder=bucket,
                identity_name=identity,
                video_ext=ext,
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
                from hexmedia.services.ingest.utils import sha256_of_file  # local import
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
            try:
                from sqlalchemy.exc import SQLAlchemyError  # noqa: F401
                with self.db.begin_nested():  # SAVEPOINT for this item only
                    # 3) insert (no commit here; transactional_session handles outer commit)
                    self.repo.create_media_item(mi)  # repo should only add/flush/refresh

                    # 4) move last (if this fails, we roll back the savepoint)
                    item_dir = ensure_item_dir(media_root, bucket, identity)
                    _ = move_into_item_dir(src, item_dir, identity, ext)

                # If we get here, both DB insert and move succeeded for this item
                rpt.created += 1
                rpt.moved += 1

            except Exception as ex:
                # Roll back this item’s DB changes (savepoint)
                try:
                    self.db.rollback()  # rolls back to the nearest savepoint if inside begin_nested
                except Exception:
                    pass
                rpt.add_error(
                    f"IngestWorker: db+move transactional unit failed for {src}: {ex}"
                )
                continue

        rpt.stop()
        return rpt
