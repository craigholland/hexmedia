from __future__ import annotations

from typing import Optional, List
from uuid import UUID as UUID_t

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hexmedia.database.core.main import Base
from hexmedia.database.core.service_object import ServiceObject
from hexmedia.domain.enums.person_role import PersonRole


class Tag(ServiceObject, Base):
    __tablename__ = "tag"

    # ServiceObject contributes id, timestamps, etc.

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # for v1, keep as TEXT; later we can cast to LTREE
    path: Mapped[str] = mapped_column(Text, nullable=False)
    is_deprecated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    media_items: Mapped[List["MediaItem"]] = relationship(
        "MediaItem",
        secondary="media_tag",
        back_populates="tags",
    )


class MediaTag(Base):
    """
    Association table; composite PK, so do NOT inherit ServiceObject.
    """
    __tablename__ = "media_tag"

    media_item_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tag.id", ondelete="CASCADE"),
        primary_key=True,
    )


class Person(ServiceObject, Base):
    __tablename__ = "person"

    # ServiceObject contributes id, timestamps, etc.

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[Optional[str]] = mapped_column(String(255))

    media_items: Mapped[List["MediaItem"]] = relationship(
        "MediaItem",
        secondary="media_person",
        back_populates="people",
    )


class MediaPerson(Base):
    """
    Association table; composite PK, so do NOT inherit ServiceObject.
    """
    __tablename__ = "media_person"

    media_item_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    person_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("person.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[PersonRole] = mapped_column(
        SAEnum(PersonRole, name="person_role"),
        nullable=False,
        server_default=text("'actor'"),
    )
