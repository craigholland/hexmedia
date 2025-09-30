# hexmedia/services/ingest/worker.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

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
        prober: Optional[MediaProbePort] = None,
    ) -> None:
        self.db = db
        self.cfg = get_settings()

        self.repo: SqlAlchemyMediaRepo = repo or SqlAlchemyMediaRepo(db)
        self.planner = planner or IngestPlanner(query_repo=self.repo)
        self.prober: MediaProbePort = prober or FFprobeAdapter()

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
            midentity = MediaIdentity(
                media_folder=bucket,
                identity_name=identity,
                video_ext=ext
            )
            probe_res = None
            # 1) probe & enrich (non-fatal on failure)
            try:
                probe_res = self.prober.probe(src)
            except Exception as ex:
                rpt.add_error(f"probe failed for {src}: {ex}")

            # 2) filesystem placement
            if not rpt.error_details:
                try:
                    item_dir = ensure_item_dir(media_root, bucket, identity)
                    dest_path = move_into_item_dir(src, item_dir, identity, ext)
                except Exception as ex:
                    rpt.add_error(f"fs move failed for {src}: {ex}")
                    continue

            # 3) initial DB row
            if not rpt.error_details:
                try:
                    size_bytes = dest_path.stat().st_size
                    sha256 = sha256_of_file(dest_path)
                    mi = MediaItem(
                        kind=item["kind"],
                        identity=midentity,
                        size_bytes=size_bytes,
                        hash_sha256=sha256,
                    )
                    if probe_res:
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

                        self.repo.create_media_item(mi)
                except Exception as ex:
                    rpt.add_error(f"db add failed for {dest_path}: {ex}")
                    continue
        rpt.stop()
        return rpt
