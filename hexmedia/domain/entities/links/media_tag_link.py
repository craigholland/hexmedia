# hexmedia/domain/entities/links/media_tag_link.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class MediaTagLink:
    """
    Join entity connecting a MediaItem and a Tag.
    DB/Policy typically enforce that (media_item_id, tag_id) is unique.
    """
    media_item_id: UUID
    tag_id: UUID
