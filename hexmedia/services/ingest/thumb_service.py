# hexmedia/services/ingest/thumb_service.py
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from hexmedia.common.settings import get_settings
from hexmedia.database.repos.media_asset_repo import SqlAlchemyMediaAssetRepo
from hexmedia.database.repos.media_query import MediaQueryRepo
from hexmedia.services.ingest.thumb_worker import ThumbWorker


@dataclass
class ThumbRunReport:
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    scanned: int = 0
    generated: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)

    def start(self): self.started_at = datetime.now()
    def stop(self): self.finished_at = datetime.now()

class ThumbService:
    def __init__(self, session: Session):
        self.session = session
        self.cfg = get_settings()
        self.q = MediaQueryRepo(session)
        self.w = SqlAlchemyMediaAssetRepo(session)

    def run(
        self,
        *,
        limit: int,
        workers: Optional[int],
        regenerate: bool,
        include_missing: bool,
        thumb_format: str,
        collage_format: str,
        thumb_width: int,
        tile_width: int,
        upscale_policy: str,
    ) -> ThumbRunReport:
        rep = ThumbRunReport()
        rep.start()

        # 1) Get candidates
        cands = self.q.find_video_candidates_for_thumbs(limit=limit, regenerate=regenerate)
        if not cands:
            rep.stop()
            return rep

        # 2) Build worker
        tw = ThumbWorker(
            media_root=self.cfg.media_root,
            query_repo=self.q,
            asset_repo=self.w,
            regenerate=regenerate,
            include_missing=include_missing,
            thumb_format=thumb_format or self.cfg.thumb_format,
            collage_format=(collage_format or thumb_format or self.cfg.collage_format),
            thumb_width=thumb_width or self.cfg.thumb_width,
            tile_width=tile_width or self.cfg.collage_tile_width,
            upscale_policy=upscale_policy or self.cfg.upscale_policy,
        )

        max_workers = min(workers or 1, self.cfg.max_thumb_workers)
        rep.scanned = len(cands)

        # 3) Fan out → aggregate results
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(tw.process_one, mid, rel_dir, fname)
                for (mid, rel_dir, fname) in cands
            ]
            for fut in as_completed(futures):
                try:
                    r = fut.result()
                except Exception as e:
                    rep.errors += 1
                    rep.error_details.append(str(e))
                    continue

                # tolerate workers returning None or non-dicts
                if not isinstance(r, dict):
                    continue

                # aggregate safely with defaults
                rep.generated += int(r.get("generated", 0) or 0)
                rep.updated  += int(r.get("updated", 0) or 0)
                rep.skipped  += int(r.get("skipped", 0) or 0)
                rep.errors   += int(r.get("errors", 0) or 0)

                # optional error fields from workers
                err = r.get("error") or r.get("error_detail") or r.get("error_details")
                if err:
                    if isinstance(err, (list, tuple)):
                        rep.error_details.extend(map(str, err))
                    else:
                        rep.error_details.append(str(err))

        rep.stop()
        return rep
