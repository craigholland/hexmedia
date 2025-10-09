# services/schemas/ingest.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class IngestPlanItemSchema(BaseModel):
    src: str = Field(..., description="Absolute path to the source file",
                     examples=["/media/hexmedia/incoming/foo.mp4"])
    media_folder: str = Field(..., examples=["aaa"])  # bucket only
    identity_name: str = Field(..., min_length=12, max_length=12, examples=["abc123def456"])
    ext: str = Field(..., examples=["mp4"])
    dest_rel_dir: str = Field(..., examples=["aaa/abc123def456"])
    dest_filename: str = Field(..., examples=["abc123def456.mp4"])
    bucket: str = Field(..., min_length=3, max_length=3, examples=["aaa"], pattern=r"^[0-9a-z]{3}")
    item: str = Field(..., min_length=12, max_length=12, examples=["abc123def456"])
    kind: str = Field(..., examples=["video", "image", "sidecar", "unknown"])
    supported: bool = Field(...)

    model_config = {
        "json_encoders": {Path: str}
    }


class IngestRunResponse(BaseModel):
    ok: bool
    started_at: datetime
    finished_at: datetime
    error_details: List[str]
    items: List[dict] = Field(default_factory=list)
    planned_items: Optional[List[IngestPlanItemSchema]] = None

class IngestRunRequest(BaseModel):

    # Optional: explicitly specify files; if omitted, service scans incoming_root
    files: Optional[List[str]] = Field(
        None, description="Absolute paths to ingest; overrides auto-scan if set"
    )
    # Room for growth:
    # max_files: Optional[int] = None
    # include_images: Optional[bool] = None
    # include_videos: Optional[bool] = None