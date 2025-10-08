# hexmedia/database/models/person.py
from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from uuid import UUID as UUID_t

from sqlalchemy import (
    ForeignKey, String, Text, UniqueConstraint, Enum as SAEnum, text, func, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hexmedia.database.core.main import Base
from hexmedia.database.core.service_object import ServiceObject
from hexmedia.domain.enums import PersonRole

if TYPE_CHECKING:
    from .media import MediaItem


def _t(name: str):
    """Return Table object from metadata, honoring schema on Base.metadata."""
    schema = Base.metadata.schema  # e.g. "hexmedia"
    key = f"{schema}.{name}" if schema else name
    return Base.metadata.tables[key]


# =======================
# People
# =======================
class Person(ServiceObject, Base):
    """
    New Person model:
      - display_name, normalized_name
      - optional notes, avatar_asset_id
      - many-to-many with PersonAlias through person_alias_link
    """
    __tablename__ = "people"
    __table_args__ = (
        Index("ix_people_display_name_trgm", "display_name", postgresql_ops={"display_name": "gin_trgm_ops"}, postgresql_using="gin"),
        Index("ix_people_normalized_name", "normalized_name"),
    )

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    avatar_asset_id: Mapped[Optional[UUID_t]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_asset.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Media links (association table kept as "media_person")
    media_items: Mapped[List["MediaItem"]] = relationship(
        "MediaItem",
        secondary=lambda: _t("media_person"),
        back_populates="people",
    )

    # Alias links (M:M via person_alias_link)
    aliases: Mapped[List["PersonAlias"]] = relationship(
        "PersonAlias",
        secondary=lambda: _t("person_alias_link"),
        back_populates="people",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Person id={self.id} name={self.display_name!r}>"


class PersonAlias(ServiceObject, Base):
    """
    Aliases are global and can attach to multiple persons (M:M).
    We keep a global uniqueness on alias_normalized for dedup.
    """
    __tablename__ = "person_alias"
    __table_args__ = (
        UniqueConstraint("alias_normalized", name="uq_person_alias_normalized_global"),
    )

    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    people: Mapped[List["Person"]] = relationship(
        "Person",
        secondary=lambda: _t("person_alias_link"),
        back_populates="aliases",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PersonAlias id={self.id} alias={self.alias!r}>"


class PersonAliasLink(Base):
    """
    Association table for Person <-> PersonAlias (M:M).
    """
    __tablename__ = "person_alias_link"
    __table_args__ = (
        UniqueConstraint("person_id", "alias_id", name="uq_person_alias_link_person_alias"),
        Index("ix_person_alias_link_alias_id", "alias_id"),
    )

    person_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        primary_key=True,
    )
    alias_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("person_alias.id", ondelete="CASCADE"),
        primary_key=True,
    )


class MediaPerson(Base):
    """
    Association table for MediaItem <-> Person with a role.
    Note the FK now points to 'people.id' (new table).
    """
    __tablename__ = "media_person"
    __table_args__ = (
        UniqueConstraint("media_item_id", "person_id", name="uq_media_person_pair"),
        Index("ix_media_person_media_item_id", "media_item_id"),
        Index("ix_media_person_person_id", "person_id"),
    )

    media_item_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    person_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[PersonRole] = mapped_column(
        SAEnum(PersonRole, name="person_role"),
        nullable=False,
        server_default=text("'actor'"),
    )