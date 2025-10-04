from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

class MediaTagAttach(BaseModel):
    tag_id: Optional[UUID] = None

    group_path: Optional[str] = None
    tag_slug: Optional[str] = None

class MediaTagRead(BaseModel):
    media_item_id: UUID
    tag_id: UUID
