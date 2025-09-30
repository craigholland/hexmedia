# hexmedia/database/repos/media_repo.py
from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from hexmedia.database.models import MediaItem as DBMediaItem
from hexmedia.domain.entities.media_item import MediaItem, MediaIdentity  # if/when you map fully
from hexmedia.domain.ports.repositories import MediaQueryPort


class MediaQueryRepo(MediaQueryPort):
    """
    Read-only queries for MediaItem, implementing MediaQueryPort so it can be
    used anywhere a port is expected (e.g., IngestPlanner).
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ---------- Methods the planner uses ----------

    def iter_media_folders(self) -> Iterable[str]:
        """
        Yield media_folder strings like '00/abc123def456'.
        """
        stmt = select(DBMediaItem.media_folder)
        for (mf,) in self.session.execute(stmt):
            if mf:
                yield mf

    def count_media_items_by_bucket(self) -> dict[str, int]:
        """
        Return counts grouped by first path segment of media_folder.
        Example: {'00': 123, '01': 98, ...}
        """
        bucket = func.split_part(DBMediaItem.media_folder, "/", 1)
        stmt = select(bucket.label("bucket"), func.count().label("n")).group_by(bucket)
        rows = self.session.execute(stmt).all()
        return {b: int(n) for (b, n) in rows if b}

    # ---------- Useful utility ----------

    def exists_hash(self, sha256: str) -> bool:
        """
        True if a row exists with the given SHA-256 hash.
        """
        stmt = select(func.count()).select_from(DBMediaItem).where(DBMediaItem.hash_sha256 == sha256)
        return self.session.execute(stmt).scalar_one() > 0

    # ---------- Stubs to complete the port ----------
    # You can implement these when you wire full domain<->DB mapping.

    def get_by_id(self, media_item_id: UUID) -> Optional[MediaItem]:
        raise NotImplementedError("get_by_id not implemented yet")

    def get_by_identity(self, identity: MediaIdentity) -> Optional[MediaItem]:
        raise NotImplementedError("get_by_identity not implemented yet")
