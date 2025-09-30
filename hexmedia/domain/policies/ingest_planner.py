from __future__ import annotations

import hashlib
import os
import string
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Tuple, TypedDict, Union

from hexmedia.common.settings import get_settings
from hexmedia.common.logging import get_logger

logger = get_logger()

# ---------- Public, JSON-friendly plan item shape ----------

class IngestPlanItem(TypedDict):
    # input
    src: str                      # absolute path to incoming file
    ext: str                      # extension without dot (lowercase)
    kind: str                     # "video" | "image" | "sidecar" | "unknown"
    supported: bool

    # identity / placement
    bucket: str                   # 3-char base36 bucket, e.g. "aaa"
    item: str                     # 12-char identity
    media_folder: str             # == bucket (kept for API clarity)
    identity_name: str            # == item

    # destination (relative to cfg.media_root)
    dest_rel_dir: str             # "<bucket>/<identity>"
    dest_filename: str            # "<identity>.<ext>"


# ---------- Optional repo duck-type (don’t import DB layer here) ----------

class _MediaQueryLike:
    # def count_media_items_by_bucket(self) -> Dict[str, int]: ...
    # def iter_media_folders(self) -> Iterable[str]: ...
    pass


# ---------- Planner implementation ----------

class IngestPlanner:
    """
    Turns a set of incoming files into a concrete “plan”:
      - choose a 3-char base36 bucket (balanced by current counts)
      - generate a 12-char identity
      - compute destination relative paths

    NOTE: The *incoming* directory does not use buckets; only the *media* tree does.
    """

    def __init__(self, query_repo: Optional[_MediaQueryLike] = None) -> None:
        self.cfg = get_settings()
        self._q = query_repo

        # normalize configured extensions
        self._video_exts = {e.strip().lower() for e in self.cfg.video_exts}
        self._image_exts = {e.strip().lower() for e in self.cfg.image_exts}
        self._sidecar_exts = {e.strip().lower() for e in self.cfg.sidecar_exts}
        self._all_exts = self._video_exts | self._image_exts | self._sidecar_exts

        # cap on number of MediaItems per Bucket
        self._bucket_max: int = int(self.cfg.hexmedia_bucket_max)
        self._bucket_chars: str = string.digits + string.ascii_lowercase

    # ----- main API -----

    def plan(self, files: Iterable[Path]) -> List[IngestPlanItem]:
        files = list(files or [])
        counts = self.get_bucket_counts()  # existing media balance

        items: List[IngestPlanItem] = []
        for src in files:
            src = Path(src)
            ext = self._ext_of(src)
            kind = self._classify_kind(ext)
            supported = ext in self._all_exts

            # pick bucket irrespective of support; keeps layout deterministic in dry runs
            bucket = self._choose_bucket(counts)
            identity = self._identity_for(src)

            items.append(
                {
                    "src": str(src),
                    "ext": ext,
                    "kind": kind,
                    "supported": supported,
                    "bucket": bucket,
                    "item": identity,
                    "media_folder": bucket,         # DB: media_folder == bucket only
                    "identity_name": identity,      # DB: identity_name
                    "dest_rel_dir": f"{bucket}/{identity}",
                    "dest_filename": f"{identity}.{ext}" if ext else identity,
                }
            )

            # increment the bucket count so subsequent choices balance
            counts[bucket] += 1

        return items

    def _sort_counts(self, ct):
        sorted_counts = dict(sorted(ct.items(), key=lambda x: x[1], reverse=True))
        d = defaultdict(int)
        d.update(**sorted_counts)
        return d

    def get_bucket_counts(self) -> DefaultDict[str, int]:
        """
        Return current MediaItem counts per bucket.
        Prefer the repository; fall back to filesystem counts under media_root.
        """
        counts: DefaultDict[str, int] = defaultdict(int)

        # 1) Repository path (fast + authoritative)
        if self._q is not None:
            fast = getattr(self._q, "count_media_items_by_bucket", None)
            if callable(fast):
                for b, n in fast().items():
                    counts[b] = int(n)
                return self._sort_counts(counts)

            # fallback repo API: iterate media_folders and tally buckets
            it = getattr(self._q, "iter_media_folders", None)
            if callable(it):
                for mf in it():
                    bucket = (mf.split("/", 1)[0]) if mf else ""
                    if bucket:
                        counts[bucket] += 1
                return self._sort_counts(counts)

        # 2) FS fallback: count item directories inside each bucket dir
        media_root: Path = self.cfg.media_root
        if media_root.exists():
            for bucket_dir in sorted(p for p in media_root.iterdir() if p.is_dir()):
                try:
                    n = sum(1 for d in bucket_dir.iterdir() if d.is_dir())
                except Exception:
                    n = 0
                counts[bucket_dir.name] = n
        return self._sort_counts(counts)

    # ----- helpers -----

    @staticmethod
    def _ext_of(p: Path) -> str:
        return p.suffix[1:].lower() if p.suffix else ""

    def _classify_kind(self, ext: str) -> str:
        if ext in self._video_exts:
            return "video"
        if ext in self._image_exts:
            return "image"
        if ext in self._sidecar_exts:
            return "sidecar"
        return "unknown"

    # ---- bucket choice (3-char base36) ----
    def _bucket_name_converter(self, val:Union[int, str]):
        base = 36
        max_int = base ** 3  # 46656

        # Convert base-10 int to base-36 str (max 3-characters long)
        if isinstance(val, int) and 0 < val <= max_int:
            digits = self._bucket_chars
            a = val // (base * base)
            b = (val // base) % base
            c = val % base
            return f"{digits[a]}{digits[b]}{digits[c]}"

        # Convert base-36 str to base-10
        elif isinstance(val, str) and len(val) < 4:
            val = val.lower().rjust(3, "0")
            digits = {ch: i for i, ch in enumerate(self._bucket_chars)}
            try:
                a, b, c = (digits[val[0]], digits[val[1]], digits[val[2]])
            except KeyError:
                raise ValueError("invalid character: only 0-9 and a-z are allowed")
            return a * (base ** 2) + b * base + c

        elif isinstance(val, int):
            raise ValueError(f"n must be in range 0..{max_int - 1} (fits in 3 base-36 chars)")
        elif isinstance(val, str):
            raise ValueError("invalid value: string inputs must be <= 3 characters")
        raise ValueError("invalid value: value must be string or integer")

    def _choose_bucket(self, counts: dict) -> str:
        """
        Determine least-filled bucket or start a new bucket
        FYI - `counts` is sorted in ascending order by value in 'get_bucket_counts()'.
        """

        biggest_bucket = "000"
        if counts:
            lowest_count = min(list(counts.values()))
            low_buckets = [b for b,v in counts.items() if v == lowest_count]
            lowest_bucket = min(low_buckets)
            if lowest_count < self._bucket_max:
                return lowest_bucket
            biggest_bucket = max(list(counts.keys()))
            next_bucket_val = self._bucket_name_converter(biggest_bucket) + 1
            return self._bucket_name_converter(next_bucket_val)

        return biggest_bucket


    def _is_valid_bucket(self, s: str) -> bool:
        if len(s) != 3:
            return False
        for ch in s:
            if not (ch.isdigit() or ("a" <= ch <= "z")):
                return False
        return True
    # ---- identity (12 chars) ----

    def _identity_for(self, p: Path) -> str:
        """
        Generate a 12-char stable identity based on file path + size + mtime.
        (Deterministic within a host; change to content-hash later if desired.)
        """
        try:
            st = p.stat()
            basis = f"{str(p.resolve())}|{st.st_size}|{int(st.st_mtime)}"
        except Exception:
            basis = str(p)

        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()
        return digest[:12]
