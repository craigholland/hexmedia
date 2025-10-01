# hexmedia/database/repos/media_query.py
from __future__ import annotations
from typing import Iterable, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from hexmedia.database.models import MediaItem as DBMediaItem
from hexmedia.domain.entities.media_item import MediaItem as DomainMediaItem, MediaIdentity

from hexmedia.database.repos._mapping import to_domain_media_item

class MediaQueryRepo:
    """
    Read-only queries for MediaItem. Satisfies MediaQueryPort via structural typing.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def iter_media_folders(self) -> Iterable[str]:
        stmt = select(DBMediaItem.media_folder)
        for (mf,) in self.session.execute(stmt):
            if mf:
                yield mf

    def count_media_items_by_bucket(self) -> dict[str, int]:
        bucket = func.split_part(DBMediaItem.media_folder, "/", 1)
        stmt = select(bucket.label("bucket"), func.count().label("n")).group_by(bucket)
        rows = self.session.execute(stmt).all()
        return {b: int(n) for (b, n) in rows if b}

    def exists_hash(self, sha256: str) -> bool:
        stmt = select(func.count()).select_from(DBMediaItem).where(DBMediaItem.hash_sha256 == sha256)
        return self.session.execute(stmt).scalar_one() > 0

    def get_by_id(self, media_item_id: UUID) -> Optional[DomainMediaItem]:
        row = self.session.get(DBMediaItem, media_item_id)
        return to_domain_media_item(row) if row else None

    def get_by_identity(self, identity: MediaIdentity) -> Optional[DomainMediaItem]:
        # Include the full identity triplet for precision
        stmt = (
            select(DBMediaItem)
            .where(
                DBMediaItem.media_folder == identity.media_folder,
                DBMediaItem.identity_name == identity.identity_name,
                DBMediaItem.video_ext == identity.video_ext,
            )
            .limit(1)
        )
        row = self.session.execute(stmt).scalars().first()
        return to_domain_media_item(row) if row else None
