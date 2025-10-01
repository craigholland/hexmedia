# hexmedia/services/ingest/thumb_worker.py
from __future__ import annotations
from pathlib import Path
from typing import Optional

from hexmedia.common.settings import get_settings
from hexmedia.database.repos.media_query import MediaQueryRepo
from hexmedia.database.repos.media_asset_repo import SqlAlchemyMediaAssetWriter
from hexmedia.services.thumbs.video_thumbnail import VideoThumbnail
from hexmedia.domain.enums.asset_kind import AssetKind

class ThumbWorker:
    """
    Stateless worker that generates:
      - assets/thumb.<fmt>
      - assets/contact_sheet.<fmt>
    and upserts MediaAsset records for each.
    """
    def __init__(
        self,
        *,
        media_root: Path,
        query_repo: MediaQueryRepo,
        asset_repo: SqlAlchemyMediaAssetWriter,
        thumb_format: str,
        collage_format: str,
        thumb_width: int,
        tile_width: int,
        upscale_policy: str,
        include_missing: bool,
        regenerate: bool,
    ) -> None:
        self.media_root = media_root
        self.q = query_repo
        self.w = asset_repo
        self.thumb_format = thumb_format
        self.collage_format = collage_format
        self.thumb_width = thumb_width
        self.tile_width = tile_width
        self.upscale_policy = upscale_policy
        self.include_missing = include_missing
        self.regenerate = regenerate

    def process_one(self, media_item_id: str, rel_dir: str, file_name: str) -> dict:
        """
        Returns counters: {"generated": int, "updated": int, "skipped": int, "errors": int}
        """
        out = {"generated": 0, "updated": 0, "skipped": 0, "errors": 0}
        item_dir = self.media_root / rel_dir
        video_path = item_dir / file_name
        assets_dir = item_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        if not video_path.exists():
            if not self.include_missing:
                out["skipped"] += 1
                return out

        vt = VideoThumbnail(video_path)

        # 1) thumb ~10%
        tpath = assets_dir / f"thumb.{self.thumb_format}"
        try:
            vt.generate_thumbnail(
                out_path=tpath,
                percent=0.10,
                target_width=self.thumb_width,
                format=self.thumb_format,
                allow_upscale=self.upscale_policy,
            )
            w, h = self._image_size_or_none(tpath)
            self.w.upsert_asset(
                media_item_id=media_item_id,
                kind=AssetKind.thumb,           # <-- adjust if your enum value differs
                rel_path=str(Path("assets") / tpath.name).replace("\\", "/"),
                width=w, height=h,
            )
            out["generated"] += 1
            out["updated"] += 1
        except Exception:
            out["errors"] += 1
            return out  # stop early; keep consistent pair generation

        # 2) contact sheet 3x3
        spath = assets_dir / f"contact_sheet.{self.collage_format}"
        try:
            sheet = vt.generate_collage(
                out_path=spath,
                percents=(10,20,30,40,50,60,70,80,90),
                tile_width=self.tile_width,
                grid=(3,3),
                format=self.collage_format,
                allow_upscale=self.upscale_policy,
            )
            if sheet is not None:
                w, h = self._image_size_or_none(spath)
                self.w.upsert_asset(
                    media_item_id=media_item_id,
                    kind=AssetKind.contact_sheet,   # <-- adjust if needed
                    rel_path=str(Path("assets") / spath.name).replace("\\", "/"),
                    width=w, height=h,
                )
                out["generated"] += 1
                out["updated"] += 1
            else:
                out["skipped"] += 1
        except Exception:
            out["errors"] += 1

        return out

    @staticmethod
    def _image_size_or_none(path: Path) -> tuple[Optional[int], Optional[int]]:
        try:
            from PIL import Image
            with Image.open(path) as im:
                return im.size
        except Exception:
            return None, None
