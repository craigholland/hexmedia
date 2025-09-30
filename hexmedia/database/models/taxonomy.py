from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID as UUID_t

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hexmedia.database.core.main import Base
from hexmedia.database.core.service_object import ServiceObject
from hexmedia.domain.enums.person_role import PersonRole

if TYPE_CHECKING:
    from .media import MediaItem

def _t(name: str):
    schema = Base.metadata.schema  # e.g. "hexmedia"
    key = f"{schema}.{name}" if schema else name
    return Base.metadata.tables[key]

class Tag(ServiceObject, Base):
    __tablename__ = "tag"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    media_items: Mapped[List["MediaItem"]] = relationship(
        "MediaItem", secondary=lambda: _t("media_tag"), back_populates="tags"
    )


class MediaTag(Base):
    __tablename__ = "media_tag"

    media_item_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_item.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True
    )


class Person(ServiceObject, Base):
    __tablename__ = "person"

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[Optional[str]] = mapped_column(String(255))

    media_items: Mapped[List["MediaItem"]] = relationship(
        "MediaItem", secondary=lambda: _t("media_person"), back_populates="people"
    )


class MediaPerson(Base):
    __tablename__ = "media_person"

    media_item_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_item.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True), ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[PersonRole] = mapped_column(
        SAEnum(PersonRole, name="person_role"), nullable=False, server_default=text("'actor'")
    )
