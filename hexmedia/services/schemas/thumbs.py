# hexmedia/services/schemas/thumbs.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field

class ThumbRequest(BaseModel):
    limit: int = Field(50, ge=1, le=1000)
    workers: Optional[int] = Field(None, ge=1, le=64)  # actual cap is in settings.MAX_THUMB_WORKERS
    regenerate: bool = False
    include_missing: bool = False
    thumb_format: str = Field("png", pattern="^(png|jpg|jpeg|webp)$")
    collage_format: Optional[str] = Field(None, pattern="^(png|jpg|jpeg|webp)$")
    thumb_width: int = Field(960, ge=64, le=4096)
    tile_width: int = Field(400, ge=64, le=4096)
    upscale_policy: Literal["never", "if_smaller_than", "always"] = "if_smaller_than"

class ThumbResponse(BaseModel):
    started_at: datetime
    finished_at: datetime
    scanned: int
    generated: int
    updated: int
    skipped: int
    errors: int
    error_details: List[str] = Field(default_factory=list)

class ThumbPlanItem(BaseModel):
    media_item_id: str = Field(..., examples=["8b7d8a2a-..."])
    rel_dir: str       = Field(..., examples=["000/abc123def456"])
    file_name: str     = Field(..., examples=["abc123def456.mp4"])