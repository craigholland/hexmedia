# hexmedia/domain/dataclasses/reports.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Base report (shared fields + utilities)
# ---------------------------------------------------------------------------
@dataclass
class BaseReport:
    """Common report base:
    - timing: started_at / finished_at
    - error capture: error_details
    - helpers: start(), stop(), add_error(), as_dict()
    """
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    # Each tuple is (subject/id/path, message)
    error_details: List[Tuple[str, str]] = field(default_factory=list)

    def start(self) -> None:
        if self.started_at is None:
            self.started_at = datetime.now()

    def stop(self) -> None:
        self.finished_at = datetime.now()

    def add_error(self, subject: str, message: str) -> None:
        self.error_details.append((subject, message))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Thumbnail generation report
# ---------------------------------------------------------------------------
@dataclass
class ThumbReport(BaseReport):
    planned: int = 0
    generated: int = 0
    skipped: int = 0
    errors: int = 0

    def merge(self, other: "ThumbReport") -> "ThumbReport":
        self.planned += other.planned
        self.generated += other.generated
        self.skipped += other.skipped
        self.errors += other.errors
        self.error_details.extend(other.error_details)
        # prefer earliest start and latest finish
        if self.started_at is None or (other.started_at and other.started_at < self.started_at):
            self.started_at = other.started_at
        if other.finished_at and (self.finished_at is None or other.finished_at > self.finished_at):
            self.finished_at = other.finished_at
        return self


# ---------------------------------------------------------------------------
# Probe (ffprobe) report
# ---------------------------------------------------------------------------
@dataclass
class ProbeReport(BaseReport):
    planned: int = 0
    probed_ok: int = 0
    not_supported: int = 0     # e.g., non-media or extensions we skip
    missing_files: int = 0
    errors: int = 0

    def merge(self, other: "ProbeReport") -> "ProbeReport":
        self.planned += other.planned
        self.probed_ok += other.probed_ok
        self.not_supported += other.not_supported
        self.missing_files += other.missing_files
        self.errors += other.errors
        self.error_details.extend(other.error_details)
        if self.started_at is None or (other.started_at and other.started_at < self.started_at):
            self.started_at = other.started_at
        if other.finished_at and (self.finished_at is None or other.finished_at > self.finished_at):
            self.finished_at = other.finished_at
        return self


# ---------------------------------------------------------------------------
# Ingest report
# ---------------------------------------------------------------------------
@dataclass
class IngestReport(BaseReport):
    planned: int = 0          # items considered by the plan
    hashed: int = 0           # files successfully hashed
    duplicates: int = 0       # skipped due to duplicate hash
    moved: int = 0            # files moved into media tree
    created: int = 0          # DB rows created (media items)
    updated: int = 0          # DB rows updated (rare; overwrite or upsert)
    errors: int = 0

    # Arbitrary counters you might want to surface (extensible without schema churn)
    extra: Dict[str, Any] = field(default_factory=dict)

    def bump(self, key: str, inc: int = 1) -> None:
        """Increment an arbitrary extra counter, e.g., 'name_collisions'."""
        self.extra[key] = int(self.extra.get(key, 0)) + inc

    def merge(self, other: "IngestReport") -> "IngestReport":
        self.planned += other.planned
        self.hashed += other.hashed
        self.duplicates += other.duplicates
        self.moved += other.moved
        self.created += other.created
        self.updated += other.updated
        self.errors += other.errors
        self.error_details.extend(other.error_details)
        # merge extras (sum int-ish values, overwrite otherwise)
        for k, v in other.extra.items():
            if isinstance(v, (int, float)) and isinstance(self.extra.get(k), (int, float)):
                self.extra[k] = self.extra.get(k, 0) + v
            elif k not in self.extra:
                self.extra[k] = v
        if self.started_at is None or (other.started_at and other.started_at < self.started_at):
            self.started_at = other.started_at
        if other.finished_at and (self.finished_at is None or other.finished_at > self.finished_at):
            self.finished_at = other.finished_at
        return self
