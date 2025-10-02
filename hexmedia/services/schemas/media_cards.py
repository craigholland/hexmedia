from __future__ import annotations
from typing import List, Optional
from pydantic import ConfigDict

from hexmedia.services.schemas import TagRead, MediaItemRead, PersonRead, MediaAssetRead


class MediaItemCardRead(MediaItemRead):
    # Embedded, only present if requested via `include`
    assets: Optional[List[MediaAssetRead]] = None
    persons: Optional[List[PersonRead]] = None
    tags: Optional[List[TagRead]] = None
    rating: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
