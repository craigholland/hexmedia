# hexmedia/domain/entities/media_asset.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from hexmedia.domain.enums.asset_kind import AssetKind


@dataclass
class MediaAsset:
    """
    Represents a derivative/auxiliary file produced for a media item
    (thumbnail, preview, subtitle, waveform, etc.).
    Uniqueness policy is typically: (media_item_id, kind) is unique.
    """
    id: Optional[UUID] = None
    media_item_id: UUID = None  # required
    kind: AssetKind = None      # required

    # File location relative to the item's identity directory (e.g., "assets/thumb.jpg").
    rel_path: str = ""          # required (non-empty)

    # Optional characteristics
    width: Optional[int] = None
    height: Optional[int] = None
    generated_at: Optional[datetime] = None

    data_origin: Optional[str] = None

    def __post_init__(self):
        if not self.media_item_id:
            raise ValueError("media_item_id is required")
        if not self.kind:
            raise ValueError("asset kind is required")
        if not self.rel_path or not self.rel_path.strip():
            raise ValueError("rel_path is required")
        if self.width is not None and self.width < 0:
            raise ValueError("width must be >= 0")
        if self.height is not None and self.height < 0:
            raise ValueError("height must be >= 0")
