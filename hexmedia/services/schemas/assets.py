from __future__ import annotations

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from hexmedia.domain.enums.asset_kind import AssetKind


class MediaAssetBase(BaseModel):
    kind: AssetKind
    rel_path: str
    width: Optional[int] = None
    height: Optional[int] = None


class MediaAssetCreate(MediaAssetBase):
    media_item_id: UUID


class MediaAssetUpdate(BaseModel):
    # kind is intentionally omitted to avoid violating the (media_item_id, kind) uniqueness
    rel_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class MediaAssetRead(MediaAssetBase):
    id: UUID
    media_item_id: UUID
    url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
