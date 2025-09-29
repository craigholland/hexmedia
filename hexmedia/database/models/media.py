from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID as UUID_t

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    BigInteger,
    Numeric,
    String,
    Text,
    text,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hexmedia.database.core.main import Base
from hexmedia.database.core.service_object import ServiceObject
from hexmedia.domain.enums.media_kind import MediaKind
from hexmedia.domain.enums.asset_kind import AssetKind


class MediaItem(ServiceObject, Base):
    __tablename__ = "media_item"
    __table_args__ = (
        UniqueConstraint(
            "media_folder",
            "identity_name",
            "video_ext",
            name="uq_mediaitem_folder_identity_ext",
        ),
        Index("ix_mediaitem_folder_identity", "media_folder", "identity_name"),
    )

    # ServiceObject contributes:
    #   id: Mapped[UUID_t]
    #   date_created: Mapped[datetime | None]
    #   last_updated: Mapped[datetime | None]
    #   data_origin, meta_data

    kind: Mapped[MediaKind] = mapped_column(SAEnum(MediaKind, name="media_kind"), nullable=False)

    # filesystem identity
    media_folder: Mapped[str] = mapped_column(Text, nullable=False)
    identity_name: Mapped[str] = mapped_column(Text, nullable=False)
    video_ext: Mapped[str] = mapped_column(String(16), nullable=False)

    # file stats
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    created_ts: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    modified_ts: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )

    # hashes/similarity
    hash_sha256: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    phash: Mapped[Optional[int]] = mapped_column(BigInteger)

    # technical (videos/images)
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    fps: Mapped[Optional[float]] = mapped_column(Numeric(8, 3))
    bitrate: Mapped[Optional[int]] = mapped_column(Integer)
    codec_video: Mapped[Optional[str]] = mapped_column(Text)
    codec_audio: Mapped[Optional[str]] = mapped_column(Text)
    container: Mapped[Optional[str]] = mapped_column(Text)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(Text)
    has_subtitles: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    # curation
    title: Mapped[Optional[str]] = mapped_column(Text)
    release_year: Mapped[Optional[int]] = mapped_column(Integer)
    source: Mapped[Optional[str]] = mapped_column(Text)
    watched: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_played_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # relationships
    assets: Mapped[List["MediaAsset"]] = relationship(
        back_populates="media_item", cascade="all,delete-orphan", passive_deletes=True
    )
    rating: Mapped["Rating | None"] = relationship(
        back_populates="media_item",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="media_tag",
        back_populates="media_items",
    )
    people: Mapped[List["Person"]] = relationship(
        "Person",
        secondary="media_person",
        back_populates="media_items",
    )


class MediaAsset(ServiceObject, Base):
    __tablename__ = "media_asset"
    __table_args__ = (
        UniqueConstraint("media_item_id", "kind", name="uq_media_asset_item_kind"),
    )

    # ServiceObject contributes id, timestamps, etc.

    media_item_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_item.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[AssetKind] = mapped_column(SAEnum(AssetKind, name="asset_kind"), nullable=False)
    rel_path: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )

    media_item: Mapped[MediaItem] = relationship(back_populates="assets")


class Rating(Base):
    """
    Uses FK as primary key (one-to-one with MediaItem), so it must NOT inherit ServiceObject.
    """
    __tablename__ = "rating"
    __table_args__ = (
        CheckConstraint("score BETWEEN 1 AND 5", name="ck_rating_score_1_5"),
    )

    media_item_id: Mapped[UUID_t] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_item.id", ondelete="CASCADE"),
        primary_key=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )

    media_item: Mapped[MediaItem] = relationship(back_populates="rating", passive_deletes=True)
