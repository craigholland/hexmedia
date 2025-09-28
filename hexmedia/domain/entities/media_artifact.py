# hexmedia/domain/entities/media_artifact.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Tag:
    """
    Simple tagging concept. For hierarchical tags, `path` can be used as a fully
    qualified path (e.g., "genre/sci-fi/cyberpunk") while `name` is the local label.
    """
    id: Optional[UUID] = None
    name: str = ""            # required
    path: str = ""            # required (unique + not empty in DB policy)

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Tag.name is required")
        if not self.path or not self.path.strip():
            raise ValueError("Tag.path is required")


@dataclass
class Person:
    """
    Represents a person (actor, director, creator...).
    """
    id: Optional[UUID] = None
    display_name: str = ""    # required

    def __post_init__(self):
        if not self.display_name or not self.display_name.strip():
            raise ValueError("Person.display_name is required")


@dataclass
class Rating:
    """
    Rating for a media item. Policy & DB enforce *singleton per media_item_id*.
    Score bounds are intentionally constrained (0..5 inclusive).
    """
    media_item_id: UUID = None  # required
    score: int = 0              # 0..5 inclusive
    rated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.media_item_id is None:
            raise ValueError("Rating.media_item_id is required")
        if not isinstance(self.score, int):
            raise ValueError("Rating.score must be an int")
        if self.score < 0 or self.score > 5:
            raise ValueError("Rating.score must be between 0 and 5 inclusive")
