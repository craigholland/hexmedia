# hexmedia/database/repositories/media_repo.py
from __future__ import annotations

from typing import Iterable, Optional, Any, cast
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

# DB models
from hexmedia.database.models.media import MediaItem as DBMediaItem
# Domain entities / value objects
from hexmedia.domain.entities.media_item import MediaItem as DomainMediaItem, MediaIdentity
from hexmedia.domain.enums.media_kind import MediaKind
from hexmedia.common.logging import get_logger

logger = get_logger()
class SqlAlchemyMediaRepo:
    """
    SQLAlchemy-backed repository that satisfies:
      - MediaQueryPort
      - MediaMutationPort

    Notes
    -----
    • This adapter also supports a small COMPAT surface used by the current IngestWorker:
         create_media_item(kind=..., media_folder=..., identity_name=..., video_ext=..., size_bytes=..., hash_sha256=?)
      so you don't need to change your worker right now.

    • Mapping between DB and domain is intentionally minimal for v1; extend as needed.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # -------------------------------------------------------------------------
    # MediaQueryPort
    # -------------------------------------------------------------------------
    def get_by_id(self, media_item_id: UUID) -> Optional[DomainMediaItem]:
        row = self.db.get(DBMediaItem, media_item_id)
        return self._to_domain(row) if row else None

    def get_by_identity(self, identity: MediaIdentity) -> Optional[DomainMediaItem]:
        """
        Accepts a MediaIdentity value object. We expect attributes:
          - media_folder (bucket)
          - identity_name
        """
        bucket = getattr(identity, "media_folder", None) or getattr(identity, "bucket", None)
        name = getattr(identity, "identity_name", None) or getattr(identity, "name", None)
        if not bucket or not name:
            return None

        stmt = select(DBMediaItem).where(
            DBMediaItem.media_folder == str(bucket),
            DBMediaItem.identity_name == str(name),
        )
        row = self.db.execute(stmt).scalars().first()
        return self._to_domain(row) if row else None

    def exists_hash(self, sha256: str) -> bool:
        stmt = select(func.count()).select_from(DBMediaItem).where(DBMediaItem.hash_sha256 == sha256)
        return (self.db.execute(stmt).scalar_one() or 0) > 0

    def iter_media_folders(self) -> Iterable[str]:
        stmt = select(DBMediaItem.media_folder)
        for (folder,) in self.db.execute(stmt):
            yield folder

    def count_media_items_by_bucket(self) -> dict[str, int]:
        stmt = select(DBMediaItem.media_folder, func.count()).group_by(DBMediaItem.media_folder)
        return {bucket: int(n) for bucket, n in self.db.execute(stmt)}

    # -------------------------------------------------------------------------
    # MediaMutationPort
    # -------------------------------------------------------------------------
    def _import_media_item(self, item: DomainMediaItem) -> DBMediaItem:
        """
        Build a new ORM MediaItem from a domain-level MediaItem.
        NOTE: This does not add/flush/commit the instance. Caller decides persistence.

        Raises:
            ValueError: if the domain item is missing identity.
        """
        if item.identity is None:
            raise ValueError("Domain MediaItem.identity must be set before import")

        orm = DBMediaItem(
            # identity triplet
            media_folder=item.identity.media_folder,
            identity_name=item.identity.identity_name,
            video_ext=item.identity.video_ext,

            # enum
            kind=item.kind,

            # file stats / tech
            size_bytes=item.size_bytes or 0,
            created_ts=item.created_ts,
            modified_ts=item.modified_ts,

            hash_sha256=item.hash_sha256,
            phash=item.phash,

            duration_sec=item.duration_sec,
            width=item.width,
            height=item.height,
            fps=item.fps,
            bitrate=item.bitrate,
            codec_video=item.codec_video,
            codec_audio=item.codec_audio,
            container=item.container,
            aspect_ratio=item.aspect_ratio,
            language=item.language,
            has_subtitles=bool(item.has_subtitles),

            # curation
            title=item.title,
            release_year=item.release_year,
            source=item.source,
            watched=bool(item.watched),
            favorite=bool(item.favorite),
            last_played_at=item.last_played_at,
        )



        return orm
    def create_media_item(self, item: DomainMediaItem | None = None, **compat: Any):
        """
        Primary path (protocol):
            create_media_item(item: DomainMediaItem)

        COMPAT path (current worker callsite):
            create_media_item(
                kind=..., media_folder=..., identity_name=...,
                video_ext=..., size_bytes=..., hash_sha256=?,
            )
        """
        if item is None:
            # COMPAT path
            return self._create_from_kwargs(**compat)


        db_row = self._import_media_item(item)

        self.db.add(db_row)
        self.db.flush()
        self.db.refresh(db_row)
        self.db.commit()

    def update_media_item(self, item: DomainMediaItem) -> DomainMediaItem:
        """
        Protocol path: takes a DomainMediaItem and persists mutable fields.
        """
        db_row = self.db.get(DBMediaItem, cast(UUID, getattr(item, "id", None)))
        if not db_row:
            raise ValueError("MediaItem not found for update")

        # Safe, conservative field sync; extend as needed
        for name in (
            "hash_sha256",
            "duration_sec",
            "width",
            "height",
            "fps",
            "bitrate",
            "codec_video",
            "codec_audio",
            "container",
            "aspect_ratio",
            "language",
            "has_subtitles",
            "title",
            "release_year",
            "source",
            "watched",
            "favorite",
            "last_played_at",
            "size_bytes",
        ):
            if hasattr(item, name):
                setattr(db_row, name, getattr(item, name))

        self.db.flush()
        self.db.refresh(db_row)
        self.db.commit()
        return self._to_domain(db_row)

    def delete_media_item(self, media_item_id: UUID) -> None:
        row = self.db.get(DBMediaItem, media_item_id)
        if row is None:
            return
        self.db.delete(row)
        self.db.commit()

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _create_from_kwargs(self, **kw: Any) -> DomainMediaItem:
        """
        Used by current IngestWorker code path.
        Required keys:
          kind, media_folder, identity_name, video_ext, size_bytes
        Optional:
          hash_sha256
        """
        try:
            kind = kw["kind"]
            media_folder = kw["media_folder"]
            identity_name = kw["identity_name"]
            video_ext = kw["video_ext"]
            size_bytes = kw["size_bytes"]
        except KeyError as e:
            raise TypeError(f"create_media_item missing required arg: {e!s}") from e

        if isinstance(kind, str):
            kind = MediaKind(kind)

        db_row = DBMediaItem(
            kind=kind,
            media_folder=str(media_folder),
            identity_name=str(identity_name),
            video_ext=str(video_ext),
            size_bytes=int(size_bytes),
            hash_sha256=kw.get("hash_sha256"),
        )
        self.db.add(db_row)
        self.db.flush()
        self.db.refresh(db_row)
        self.db.commit()
        return self._to_domain(db_row)

    def _to_domain(self, row: DBMediaItem) -> DomainMediaItem:
        """
        Minimal mapping DB -> domain entity for v1.
        Assumes DomainMediaItem accepts these keyword args.
        Extend this as the domain model evolves.
        """
        logger.warning(f"_to_domain: is 'row' None?: {row == None}")
        entity = DomainMediaItem(
            id=row.id,
            kind=row.kind.value if isinstance(row.kind, MediaKind) else str(row.kind),
            media_folder=row.media_folder,
            identity_name=row.identity_name,
            video_ext=row.video_ext,
            size_bytes=row.size_bytes,
            hash_sha256=row.hash_sha256,
            # technical (may be None)
            duration_sec=row.duration_sec,
            width=row.width,
            height=row.height,
            fps=float(row.fps) if row.fps is not None else None,
            bitrate=row.bitrate,
            codec_video=row.codec_video,
            codec_audio=row.codec_audio,
            container=row.container,
            aspect_ratio=row.aspect_ratio,
            language=row.language,
            has_subtitles=row.has_subtitles,
            # curation
            title=row.title,
            release_year=row.release_year,
            source=row.source,
            watched=row.watched,
            favorite=row.favorite,
            last_played_at=row.last_played_at,
        )
        logger.warning(f"CRAIG: _to_domain: {entity}")
        return entity
