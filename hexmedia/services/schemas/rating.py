from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

class RatingCreate(BaseModel):
    score: int  # 1..5

class RatingRead(BaseModel):
    media_item_id: UUID
    score: int
    rated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
