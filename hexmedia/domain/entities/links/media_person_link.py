# hexmedia/domain/entities/links/media_person_link.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from hexmedia.domain.enums.person_role import PersonRole


@dataclass(frozen=True)
class MediaPersonLink:
    """
    Join entity connecting a MediaItem and a Person with a specific role.
    DB/Policy typically enforce that (media_item_id, person_id, role) is unique.
    """
    media_item_id: UUID
    person_id: UUID
    role: PersonRole
    credited_as: Optional[str] = None  # override display, if desired
