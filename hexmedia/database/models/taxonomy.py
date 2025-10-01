from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID as UUID_t

from sqlalchemy import (
    Boolean, Enum as SAEnum, ForeignKey, String,
    Text, text, UniqueConstraint, CheckConstraint,
    Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hexmedia.database.core.main import Base
from hexmedia.database.core.service_object import ServiceObject
from hexmedia.domain.enums import PersonRole, Cardinality

if TYPE_CHECKING:
    from .media import MediaItem

def _t(name: str):
    schema = Base.metadata.schema  # e.g. "hexmedia"
    key = f"{schema}.{name}" if schema else name
    return Base.metadata.tables[key]


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (
        UniqueConstraint("group_id", "slug", name="uq_tag_group_slug"),
        CheckConstraint("(parent_id IS NULL) OR (group_id IS NOT NULL)", name="ck_tag_parent_requires_group"),
    )

    id: Mapped[UUID_t] = mapped_column(primary_key=True)
    group_id: Mapped[Optional[UUID_t]] = mapped_column(ForeignKey("tag_group.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    parent_id: Mapped[Optional[UUID_t]] = mapped_column(ForeignKey("tag.id", ondelete="RESTRICT"))

    group: Mapped[Optional["TagGroup"]] = relationship(back_populates="tags")
    parent: Mapped[Optional["Tag"]] = relationship(remote_side="Tag.id")
    children: Mapped[List["Tag"]] = relationship()


class MediaTag(Base):
    __tablename__ = "media_tag"
    __table_args__ = (UniqueConstraint("media_item_id", "tag_id", name="uq_media_tag_item_tag"),)
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


class TagGroup(Base):
    __tablename__ = "tag_group"
    __table_args__ = (
        UniqueConstraint("parent_id", "key", name="uq_taggroup_parent_key"),
        UniqueConstraint("path", name="uq_taggroup_path"),
    )

    id: Mapped[UUID_t] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[UUID_t]] = mapped_column(ForeignKey("tag_group.id", ondelete="RESTRICT"))
    key: Mapped[str] = mapped_column(String(64), nullable=False)          # slug-like within the parent
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    cardinality: Mapped[Cardinality] = mapped_column(
        SAEnum(Cardinality, name="tag_cardinality"),
        nullable=False,
        server_default="multi",
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text, nullable=False)                # computed at app layer
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0) # 0=root

    parent: Mapped[Optional["TagGroup"]] = relationship(remote_side="TagGroup.id", backref="children")
    tags: Mapped[List["Tag"]] = relationship(back_populates="group")



