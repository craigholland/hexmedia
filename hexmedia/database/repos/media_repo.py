# hexmedia/database/repos/media_repo.py
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
from hexmedia.database.repos._mapping import to_domain_media_item


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
        return to_domain_media_item(row) if row else None

    def get_by_identity(self, identity: MediaIdentity) -> Optional[DomainMediaItem]:
        stmt = (
            select(DBMediaItem)
            .where(
                DBMediaItem.media_folder == identity.media_folder,
                DBMediaItem.identity_name == identity.identity_name,
                DBMediaItem.video_ext == identity.video_ext,
            )
            .limit(1)
        )
        row = self.db.execute(stmt).scalars().first()
        return to_domain_media_item(row) if row else None

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

    def create_media_item(self, item: DomainMediaItem) -> DomainMediaItem:
        self._validate_new_item(item)
        orm = self._import_media_item(item)
        self._enforce_uniques(orm)
        self._persist_core(orm)
        # If you need the PK right away, flush/refresh but DO NOT commit here:
        self.db.flush()
        self.db.refresh(orm)
        self._persist_relations(orm, item)
        return to_domain_media_item(orm)

    def update_media_item(self, item: DomainMediaItem) -> DomainMediaItem:
        db_row = self.db.get(DBMediaItem, cast(UUID, getattr(item, "id", None)))
        if not db_row:
            raise ValueError("MediaItem not found for update")

        for name in (
            "hash_sha256",
            "duration_sec", "width", "height", "fps", "bitrate",
            "codec_video", "codec_audio", "container", "aspect_ratio",
            "language", "has_subtitles",
            "title", "release_year", "source",
            "watched", "favorite", "last_played_at",
            "size_bytes",
        ):
            if hasattr(item, name):
                setattr(db_row, name, getattr(item, name))

        self.db.flush()
        self.db.refresh(db_row)
        return to_domain_media_item(db_row)

    def delete_media_item(self, media_item_id: UUID) -> None:
        row = self.db.get(DBMediaItem, media_item_id)
        if row is None:
            return
        self.db.delete(row)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _validate_new_item(self, item: DomainMediaItem) -> None:
        if item.identity is None:
            raise ValueError("MediaItem.identity is required")
        if not item.identity.video_ext:
            raise ValueError("video_ext is required")

    def _enforce_uniques(self, orm: DBMediaItem) -> None:
        # SQL-level unique constraint exists; this pre-check gives earlier error messaging if desired
        exists = self.db.query(DBMediaItem.id).filter_by(
            media_folder=orm.media_folder,
            identity_name=orm.identity_name,
            video_ext=orm.video_ext,
        ).first()
        if exists:
            raise ValueError("Media item already exists for this identity triplet")

    def _persist_core(self, orm: DBMediaItem) -> DBMediaItem:
        self.db.add(orm)
        # Do not flush/commit here; the API transaction boundary controls commit
        return orm

    def _persist_relations(self, orm: DBMediaItem, item: DomainMediaItem) -> None:
        # If you create assets/tags/people/rating alongside, centralize here.
        # Example (pseudo; adapt to your current API):
        # for asset in item.assets or []:
        #     self.session.add(MediaAsset(media_item=orm, ...))
        # if item.rating is not None:
        #     self.session.merge(Rating(media_item=orm, score=item.rating))
        pass
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

