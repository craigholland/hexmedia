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

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _sanitize_format(fmt: Optional[str]) -> str:
        """Lowercase, trim, and only allow a safe subset."""
        allowed = {"jpg", "jpeg", "png", "webp"}
        f = (fmt or "").strip().lower()
        # normalize jpeg -> jpg for consistency
        if f == "jpeg":
            f = "jpg"
        return f if f in allowed else ""

    def _resolve_format(self, requested: Optional[str], cfg_default: Optional[str], *, fallback: str) -> str:
        """
        Decide final format with precedence:
          1) valid requested value
          2) valid settings default
          3) hard fallback (png for collage, jpg for thumb)
        """
        req = self._sanitize_format(requested)
        if req:
            return req
        cfgv = self._sanitize_format(cfg_default)
        return cfgv or fallback

    # --- main ---------------------------------------------------------------

    def run(
        self,
        *,
        limit: int,
        workers: Optional[int],
        regenerate: bool,
        include_missing: bool,
        thumb_format: Optional[str],
        collage_format: Optional[str],
        thumb_width: Optional[int],
        tile_width: Optional[int],
        upscale_policy: Optional[str],
    ) -> ThumbRunReport:
        rep = ThumbRunReport()
        rep.start()

        # 1) Get candidates
        cands = self.q.find_video_candidates_for_thumbs(limit=limit, regenerate=regenerate)
        if not cands:
            rep.stop()
            return rep

        # 2) Resolve options against Settings (and sanitize)
        fmt_thumb = self._resolve_format(thumb_format, getattr(self.cfg, "thumb_format", None), fallback="jpg")
        fmt_collage = self._resolve_format(collage_format, getattr(self.cfg, "collage_format", None), fallback="png")

        tw = ThumbWorker(
            media_root=self.cfg.media_root,
            query_repo=self.q,
            asset_repo=self.w,
            regenerate=bool(regenerate),
            include_missing=bool(include_missing),
            thumb_format=fmt_thumb,
            collage_format=fmt_collage,  # <- will be "png" unless caller explicitly asked for something else valid
            thumb_width=(thumb_width or getattr(self.cfg, "thumb_width", 480)),
            tile_width=(tile_width or getattr(self.cfg, "collage_tile_width", 160)),
            upscale_policy=(upscale_policy or getattr(self.cfg, "upscale_policy", "never")),
        )

        # Thread cap: at least 1, no more than cfg
        max_workers_cfg = int(getattr(self.cfg, "max_thumb_workers", 4) or 4)
        max_workers = max(1, min(int(workers or 1), max_workers_cfg))

        rep.scanned = len(cands)

        # 3) Fan out → aggregate results
        from typing import Dict, Any
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(tw.process_one, mid, rel_dir, fname) for (mid, rel_dir, fname) in cands]
            for fut in as_completed(futures):
                try:
                    r: Dict[str, Any] = fut.result()
                except Exception as e:
                    rep.errors += 1
                    rep.error_details.append(str(e))
                    continue

                if not isinstance(r, dict):
                    continue

                rep.generated += int(r.get("generated", 0) or 0)
                rep.updated  += int(r.get("updated", 0) or 0)
                rep.skipped  += int(r.get("skipped", 0) or 0)
                rep.errors   += int(r.get("errors", 0) or 0)

                err = r.get("error") or r.get("error_detail") or r.get("error_details")
                if err:
                    if isinstance(err, (list, tuple)):
                        rep.error_details.extend(map(str, err))
                    else:
                        rep.error_details.append(str(err))

        rep.stop()
        return rep
