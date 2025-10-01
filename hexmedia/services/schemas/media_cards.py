from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from hexmedia.services.schemas.media import MediaItemRead
from hexmedia.services.schemas.assets import MediaAssetRead
from hexmedia.services.schemas.people import PersonRead

# If you already have TagRead later, you can import and uncomment below.
# from hexmedia.services.schemas.tags import TagRead

class MediaItemCardRead(MediaItemRead):
    # Embedded, only present if requested via `include`
    assets: Optional[List[MediaAssetRead]] = None
    persons: Optional[List[PersonRead]] = None
    # tags: Optional[List[TagRead]] = None
    rating: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
