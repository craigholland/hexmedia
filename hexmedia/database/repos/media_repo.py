# hexmedia/database/repos/media_repo.py
from __future__ import annotations

from typing import Iterable, Optional, Any, Union, overload
from uuid import UUID

from sqlalchemy import select, func, delete as sa_delete
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
        Build an ORM MediaItem from the domain entity.
        """
        orm = DBMediaItem(
            media_folder=item.identity.media_folder,
            identity_name=item.identity.identity_name,
            video_ext=item.identity.video_ext,
            kind=item.kind or MediaKind.video,

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
            has_subtitles=item.has_subtitles or False,

            title=item.title,
            release_year=item.release_year,
            source=item.source,
            watched=item.watched or False,
            favorite=item.favorite or False,
            last_played_at=item.last_played_at,
        )
        return orm

    def create_media_item(self, item: DomainMediaItem) -> DBMediaItem:
        # Uniqueness check on the triplet
        mf = item.identity.media_folder
        nm = item.identity.identity_name
        vx = item.identity.video_ext

        exists_stmt = (
            select(func.count())
            .select_from(DBMediaItem)
            .where(
                DBMediaItem.media_folder == mf,
                DBMediaItem.identity_name == nm,
                DBMediaItem.video_ext == vx,
            )
        )
        already = self.db.execute(exists_stmt).scalar_one()
        if already:
            raise ValueError(
                f"MediaItem already exists for triplet ({mf}/{nm}.{vx})"
            )

        orm = self._import_media_item(item)
        self.db.add(orm)
        # caller controls flush/commit
        return orm

    def _apply_domain_to_orm(self, orm: DBMediaItem, dom: DomainMediaItem) -> None:
        # Copy over updatable fields (expand as you like)
        orm.title = dom.title
        orm.watched = dom.watched
        orm.favorite = dom.favorite
        orm.last_played_at = dom.last_played_at

        # tech/details (only if you intend these to be mutable)
        orm.duration_sec = dom.duration_sec
        orm.width = dom.width
        orm.height = dom.height
        orm.fps = dom.fps
        orm.bitrate = dom.bitrate
        orm.codec_video = dom.codec_video
        orm.codec_audio = dom.codec_audio
        orm.container = dom.container
        orm.aspect_ratio = dom.aspect_ratio
        orm.language = dom.language
        orm.has_subtitles = dom.has_subtitles

        # file stats (optional)
        orm.size_bytes = dom.size_bytes
        orm.created_ts = dom.created_ts
        orm.modified_ts = dom.modified_ts
        orm.hash_sha256 = dom.hash_sha256
        orm.phash = dom.phash

    @overload
    def update_media_item(self, item: DomainMediaItem, updates: None = None) -> Optional[DBMediaItem]:
        ...

    @overload
    def update_media_item(self, item: UUID, updates: dict) -> Optional[DBMediaItem]:
        ...

    def update_media_item(
            self,
            item: Union[DomainMediaItem, UUID],
            updates: dict | None = None,
    ) -> Optional[DBMediaItem]:
        """
        - If 'item' is a DomainMediaItem -> update by its id using fields from the domain object
        - If 'item' is a UUID          -> apply 'updates' dict to that row
        Returns the ORM row or None if not found.
        """
        if isinstance(item, DomainMediaItem):
            if not item.id:
                return None
            orm = self.db.get(DBMediaItem, item.id)
            if not orm:
                return None
            self._apply_domain_to_orm(orm, item)
            return orm

        # UUID path
        media_item_id: UUID = item
        orm = self.db.get(DBMediaItem, media_item_id)
        if not orm:
            return None
        if updates:
            for k, v in updates.items():
                setattr(orm, k, v)
        return orm

    def delete_media_item(self, media_item_id: UUID) -> bool:
        """
        Delete the media item and make the deletion visible immediately within
        the same Session (tests call Session.get() right after).
        """
        obj = self.db.get(DBMediaItem, media_item_id)
        if not obj:
            return False

        # Mark as deleted, persist to DB, and evict from identity map so .get(...) returns None
        self.db.delete(obj)
        self.db.flush()
        try:
            self.db.expunge(obj)
        except Exception:
            # safe guard; expunge may raise if state already detached
            pass
        return True

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
        return self._to_domain(db_row)

