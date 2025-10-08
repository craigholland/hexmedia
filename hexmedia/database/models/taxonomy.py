# hexmedia/database/models/taxonomy.py
from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID as UUID_t

from sqlalchemy import (
    Enum as SAEnum, ForeignKey, String,
    Text, UniqueConstraint, CheckConstraint, Integer, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hexmedia.database.core.main import Base
from hexmedia.database.core.service_object import ServiceObject
from hexmedia.domain.enums import Cardinality

if TYPE_CHECKING:
    from .media import MediaItem


def _t(name: str):
    """Return Table object from metadata, honoring schema on Base.metadata."""
    schema = Base.metadata.schema  # e.g. "hexmedia"
    key = f"{schema}.{name}" if schema else name
    return Base.metadata.tables[key]


# =======================
# Tag groups (taxonomy)
# =======================
class TagGroup(ServiceObject, Base):
    __tablename__ = "tag_group"
    __table_args__ = (
        UniqueConstraint("parent_id", "key", name="uq_taggroup_parent_key"),
        UniqueConstraint("path", name="uq_taggroup_path"),
    )

    parent_id: Mapped[Optional[UUID_t]] = mapped_column(
        ForeignKey("tag_group.id", ondelete="RESTRICT")
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)           # slug-like within the parent
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    cardinality: Mapped[Cardinality] = mapped_column(
        SAEnum(Cardinality, name="tag_cardinality"),
        nullable=False,
        server_default="MULTI",
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text, nullable=False)                # computed at app layer
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")  # 0=root

    parent: Mapped[Optional["TagGroup"]] = relationship(
        "TagGroup",
        remote_side="TagGroup.id",
        back_populates="children",
    )
    children: Mapped[List["TagGroup"]] = relationship(
        "TagGroup",
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    tags: Mapped[List["Tag"]] = relationship(back_populates="group")


# =======================
# Tags
# =======================
class Tag(ServiceObject, Base):
    __tablename__ = "tag"
    __table_args__ = (
        UniqueConstraint("group_id", "slug", name="uq_tag_group_slug"),
        CheckConstraint(
            "(parent_id IS NULL) OR (group_id IS NOT NULL)",
            name="ck_tag_parent_requires_group",
        ),
        Index("ix_tag_parent_id", "parent_id"),
        Index("ix_tag_group_id", "group_id"),
    )

    group_id: Mapped[Optional[UUID_t]] = mapped_column(
        ForeignKey("tag_group.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    parent_id: Mapped[Optional[UUID_t]] = mapped_column(
        ForeignKey("tag.id", ondelete="SET NULL"),
        nullable=True,
    )

    group: Mapped[Optional["TagGroup"]] = relationship(back_populates="tags")

    # Self-referential tree
    parent: Mapped[Optional["Tag"]] = relationship(
        "Tag",
        remote_side="Tag.id",
        back_populates="children",
    )
    children: Mapped[List["Tag"]] = relationship(
        "Tag",
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    # Many-to-many to media items through association table
    media_items: Mapped[List["MediaItem"]] = relationship(
        "MediaItem",
        secondary=lambda: _t("media_tag"),
        back_populates="tags",
    )
Index("ix_tag_name_lower", func.lower(Tag.name))

class MediaTag(Base):
    __tablename__ = "media_tag"
    __table_args__ = (
        UniqueConstraint("media_item_id", "tag_id", name="uq_media_tag_item_tag"),
        Index("ix_media_tag_tag_id", "tag_id"),
    )

    media_item_id: Mapped[UUID_t] = mapped_column(
        ForeignKey("media_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID_t] = mapped_column(
        ForeignKey("tag.id", ondelete="CASCADE"),
        primary_key=True,
    )