# hexmedia/domain/policies/ingest_planner.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Dict, List

from hexmedia.common.settings import get_settings
from hexmedia.common.naming.slugger import random_slug
from hexmedia.services.ingest.utils import is_supported_media_file
from hexmedia.domain.dataclasses.ingest import IngestPlanItem

# Keep these small and explicit so tests are deterministic.
VIDEO_EXTS = {"mp4", "mkv", "mov", "avi"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
SUPPORTED_EXTS = VIDEO_EXTS | IMAGE_EXTS


class IngestPlanner:
    """
    Assigns incoming files to 3-char base36 buckets with a CAPACITY per bucket.
    Capacity is read from settings as `hexmedia_bucket_max` and represents
    HOW MANY media item folders may live under a bucket like "000".

    Bucket selection rule:
      - Prefer the lexicographically smallest existing bucket whose count < capacity.
      - If all existing buckets are full, allocate the NEXT base36 bucket key
        (e.g. after "000" comes "001", … "009", "00a", …, up to "zzz").
    """

    def __init__(self, query_repo: Optional[object]) -> None:
        self.q = query_repo
        cfg = get_settings()
        cap = int(getattr(cfg, "hexmedia_bucket_max", 1000) or 1000)
        # be defensive
        self._capacity: int = max(1, cap)

    # ---------------- public ----------------

    def plan(self, files: Iterable[Path | str]) -> List[IngestPlanItem]:
        counts = self.get_bucket_counts()  # normalized to 3-char base36 keys

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

            # Choose the first (lexicographically) bucket that is not at capacity.
            bucket = self._select_bucket(counts)
            counts[bucket] = counts.get(bucket, 0) + 1

            identity = random_slug(12)
            dest_rel_dir = f"{bucket}/{identity}"
            dest_filename = f"{identity}.{ext}" if ext else identity
            media_folder = dest_rel_dir  # existing tests expect "<bucket>/<identity>"

            out.append(
                IngestPlanItem(
                    src=src,
                    bucket=bucket,
                    item=identity,               # dataclass exposes identity_name in schemas
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
        Return counts per base36 bucket key ("000".."zzz").
        Priority:
          1) query_repo.count_media_items_by_bucket()  -> normalize keys to 3-char base36
          2) derive from query_repo.iter_media_folders() (e.g. "00/abc123" or "000/…")
          3) fallback to {"000": 0} so we start at the first bucket
        """
        counts: Dict[str, int] = {}

        # 1) direct counts (preferred)
        if self.q and hasattr(self.q, "count_media_items_by_bucket"):
            try:
                res = getattr(self.q, "count_media_items_by_bucket")()  # may return dict-like or None
                if res:
                    for k, v in dict(res).items():
                        norm = self._normalize_key(str(k))
                        if norm is not None:
                            counts[norm] = counts.get(norm, 0) + int(v or 0)
            except Exception:
                counts = {}

        # 2) derive by iterating media folders (if still empty)
        if not counts and self.q and hasattr(self.q, "iter_media_folders"):
            try:
                derived: Dict[str, int] = {}
                for mf in self.q.iter_media_folders():  # e.g. "00/abc", "000/abc", "0a9/xyz"
                    if not mf:
                        continue
                    bucket_raw = str(mf).split("/", 1)[0]
                    norm = self._normalize_key(bucket_raw)
                    if norm is None:
                        continue
                    derived[norm] = derived.get(norm, 0) + 1
                counts = derived
            except Exception:
                counts = {}

        # 3) initialize first bucket if still empty
        if not counts:
            counts = {"000": 0}

        return counts

    # ---------------- internals ----------------

    def _select_bucket(self, counts: Dict[str, int]) -> str:
        """
        Pick the first (lexicographic base36) bucket with count < capacity.
        If none exist, allocate the next base36 bucket after the current maximum.
        """
        # Try existing buckets first (smallest key first)
        for key in sorted(counts.keys(), key=self._base36_sort_key):
            if counts.get(key, 0) < self._capacity:
                return key

        # All existing buckets are full: allocate the next one.
        if counts:
            max_key = max(counts.keys(), key=self._base36_sort_key)
            next_key = self._inc_base36(max_key)
        else:
            next_key = "000"

        if next_key not in counts:
            counts[next_key] = 0
        return next_key

    # --- base36 helpers ---

    @staticmethod
    def _base36_sort_key(key: str) -> int:
        return int(key.lower(), 36)

    @staticmethod
    def _normalize_key(raw: str) -> Optional[str]:
        """
        Accepts inputs like "0", "00", "000", "2", "a9", "01", etc.
        Returns a zero-padded 3-char base36 string ("000".."zzz"),
        or None if invalid.
        """
        s = (raw or "").strip().lower()
        if not s:
            return None
        try:
            val = int(s, 36)
            if val < 0:
                return None
            base36 = IngestPlanner._to_base36(val)
            return base36.rjust(3, "0")[-3:]
        except Exception:
            return None

    @staticmethod
    def _inc_base36(key: str) -> str:
        val = int(key.lower(), 36)
        nxt = val + 1
        # cap at 'zzz' (36^3 - 1 = 46655). If you want to overflow behavior, change here.
        max_val = (36 ** 3) - 1
        if nxt > max_val:
            raise ValueError("All buckets up to 'zzz' are at capacity.")
        return IngestPlanner._to_base36(nxt).rjust(3, "0")

    @staticmethod
    def _to_base36(num: int) -> str:
        if num == 0:
            return "0"
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"
        out = []
        n = num
        while n > 0:
            n, r = divmod(n, 36)
            out.append(digits[r])
        return "".join(reversed(out))
