from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path




@dataclass(frozen=True)
class IngestPlanItem:
    """
    Dataclass returned by IngestPlanner.plan(). Tests expect attribute access
    and an identity_name alias (compat) in addition to 'item'.
    """
    src: Path
    bucket: str                # e.g. "02"
    item: str                  # identity_name
    ext: str                   # "mp4" or ""
    dest_rel_dir: str          # "<bucket>/<item>"
    dest_filename: str         # "<item>.<ext>" (or "<item>" if ext empty)
    media_folder: str          # "<bucket>/<item>"
    kind: str                  # "video" | "image" | "unknown"
    supported: bool            # True iff ext supported

    # ---- compat alias expected by tests ----
    @property
    def identity_name(self) -> str:
        return self.item

    def as_dict(self) -> dict:
        """Back-compat shim if any call site expects dicts."""
        return {
            "src": str(self.src),
            "bucket": self.bucket,
            "item": self.item,
            "ext": self.ext,
            "dest_rel_dir": self.dest_rel_dir,
            "dest_filename": self.dest_filename,
            "media_folder": self.media_folder,
            "kind": self.kind,
            "supported": self.supported,
        }

