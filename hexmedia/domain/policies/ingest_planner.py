# hexmedia/domain/policies/ingest_planner.py
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Iterable, List, Optional, Set

from pydantic import BaseModel, ConfigDict

from hexmedia.common.settings import get_settings
from hexmedia.common.naming.slugger import random_slug as random_name

# Minimal query port shape (avoid importing actual port module here)
class _MediaQueryLike:
    # Optional fast path: should return dict[str, int] mapping bucket -> count
    def count_media_items_by_bucket(self) -> dict[str, int]: ...
    # Fallback path: yield or return iterable of media_folder strings like "<bucket>/<item>"
    def iter_media_folders(self) -> Iterable[str]: ...


class IngestPlanItem(BaseModel):
    src: Path
    media_folder: str
    identity_name: str
    ext: str
    dest_rel_dir: str
    dest_filename: str
    bucket: str
    item: str
    model_config = ConfigDict(arbitrary_types_allowed=True)


class IngestPlanner:
    def __init__(self, query_repo: Optional[_MediaQueryLike] = None) -> None:
        self.cfg = get_settings()
        self._q = query_repo
        self._video_exts = {e.strip().lower() for e in self.cfg.VIDEO_EXTS}
        self._image_exts = {e.strip().lower() for e in self.cfg.IMAGE_EXTS}
        self._sidecar_exts = {e.strip().lower() for e in self.cfg.SIDECAR_EXTS}
        self._all_exts = self._video_exts | self._image_exts | self._sidecar_exts

    # ... (existing plan(), helpers, etc.) ...

    # ---------- NEW ----------
    def get_bucket_counts(self) -> DefaultDict[str, int]:
        """
        Returns a defaultdict(int) mapping bucket -> number of MediaItems.
        Prefers DB via query_repo; falls back to filesystem if no repo is provided.
        """
        counts: DefaultDict[str, int] = defaultdict(int)

        # 1) Preferred: repository fast path
        if self._q is not None:
            # Try an optimized API if the repo provides it:
            fast = getattr(self._q, "count_media_items_by_bucket", None)
            if callable(fast):
                for b, n in fast().items():
                    counts[b] = int(n)
                return counts

            # Fallback: iterate media_folders and tally first path segment as bucket
            it = getattr(self._q, "iter_media_folders", None)
            if callable(it):
                for mf in it():
                    bucket = (mf.split("/", 1)[0]) if mf else ""
                    if bucket:
                        counts[bucket] += 1
                return counts

        # 2) Filesystem fallback (best effort, not authoritative)
        media_root: Path = self.cfg.media_root
        if media_root.exists():
            for bucket_dir in sorted(p for p in media_root.iterdir() if p.is_dir()):
                # Count immediate child dirs as items (layout: media_root/<bucket>/<item>/...)
                try:
                    n = sum(1 for d in bucket_dir.iterdir() if d.is_dir())
                except Exception:
                    n = 0
                counts[bucket_dir.name] = n

        return counts
