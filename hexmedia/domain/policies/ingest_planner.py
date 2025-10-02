from __future__ import annotations

import os

from pathlib import Path
from typing import Iterable, Optional, Dict, List

from hexmedia.common.naming.slugger import random_slug
from hexmedia.services.ingest.utils import is_supported_media_file
from hexmedia.domain.dataclasses.ingest import IngestPlanItem

# Keep these small and explicit so tests are deterministic.
VIDEO_EXTS = {"mp4", "mkv", "mov", "avi"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
SUPPORTED_EXTS = VIDEO_EXTS | IMAGE_EXTS


class IngestPlanner:
    """
    Bucket-balancing + identity assignment for incoming files.

    If a query repo is provided:
      - With explicit counts: balance only across those reported buckets.
      - With iter_media_folders: derive counts from observed buckets only.
    Otherwise (no repo): initialize 00..N-1 with zeros from HEXMEDIA_BUCKET_MAX.
    """

    def __init__(self, query_repo: Optional[object]) -> None:
        self.q = query_repo
        self._bucket_max = int(os.getenv("HEXMEDIA_BUCKET_MAX", "100"))

    # ---------------- public ----------------

    def plan(self, files: Iterable[Path | str]) -> List[IngestPlanItem]:
        counts = self.get_bucket_counts()

        out: List[IngestPlanItem] = []
        for f in files:
            src = Path(f)
            ext = (src.suffix.lstrip(".") or "").lower()

            if ext in VIDEO_EXTS:
                kind = "video"
            elif ext in IMAGE_EXTS:
                kind = "image"
            else:
                kind = "unknown"

            supported = (ext in SUPPORTED_EXTS) and is_supported_media_file(src)

            # Choose bucket with smallest count (ties: lexicographically smallest)
            bucket = self._choose_bucket(counts)
            counts[bucket] = counts.get(bucket, 0) + 1

            identity = random_slug(12)
            dest_rel_dir = f"{bucket}/{identity}"
            dest_filename = f"{identity}.{ext}" if ext else identity
            media_folder = dest_rel_dir

            out.append(
                IngestPlanItem(
                    src=src,
                    bucket=bucket,
                    item=identity,
                    ext=ext,
                    dest_rel_dir=dest_rel_dir,
                    dest_filename=dest_filename,
                    media_folder=media_folder,
                    kind=kind,
                    supported=supported,
                )
            )

        return out

    def get_bucket_counts(self) -> Dict[str, int]:
        """
        Return counts per two-digit bucket key ("00".."NN").
        Robust fallback order:
          1) query_repo.count_media_items_by_bucket()
          2) derive from query_repo.iter_media_folders()
          3) initialize zeros for all buckets [0.._bucket_max)
        """
        counts: Dict[str, int] = {}

        # 1) direct counts (preferred)
        if self.q and hasattr(self.q, "count_media_items_by_bucket"):
            try:
                res = getattr(self.q, "count_media_items_by_bucket")()  # may return dict-like or None
                if res:
                    counts = dict(res)
            except Exception:
                counts = {}

        # 2) derive by iterating media folders (if still empty)
        if not counts and self.q and hasattr(self.q, "iter_media_folders"):
            try:
                derived: Dict[str, int] = {}
                for mf in self.q.iter_media_folders():  # e.g. "00/abc123..."
                    if not mf:
                        continue
                    b = str(mf).split("/", 1)[0]  # bucket is first segment
                    # normalize to two digits if numeric-ish
                    try:
                        if len(b) < 2 and b.isdigit():
                            b = f"{int(b):02d}"
                    except Exception:
                        pass
                    derived[b] = derived.get(b, 0) + 1
                counts = derived
            except Exception:
                counts = {}

        # 3) initialize zeros if still empty
        if not counts:
            counts = {f"{i:02d}": 0 for i in range(self._bucket_max)}

        return counts

    # ---------------- internals ----------------

    def _all_bucket_keys(self) -> List[str]:
        """
        Generate "00".."NN" for self._bucket_max. Two digits up to 99,
        three digits beyond (you can refine if you prefer).
        """
        width = 2 if self._bucket_max <= 100 else 3
        return [f"{i:0{width}d}" for i in range(self._bucket_max)]

    def _choose_bucket(self, counts: Dict[str, int]) -> str:
        # Smallest count first; in ties choose lexicographically smallest key
        return min(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
