# hexmedia/database/repos/media_query.py
from __future__ import annotations
from typing import Iterable, Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, aliased

from hexmedia.database.models import (
    MediaItem as DBMediaItem,
    MediaAsset as DBMediaAsset
)
from hexmedia.domain.entities.media_item import MediaItem as DomainMediaItem, MediaIdentity
from hexmedia.domain.enums.media_kind import MediaKind
from hexmedia.domain.enums.asset_kind import AssetKind
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

    def list_media_items(self, *, limit: int = 50, offset: int = 0) -> list[DomainMediaItem]:
        """
        Return a page of media items ordered by newest first.
        Router can convert to Read DTOs.
        """
        stmt = (
            select(DBMediaItem)
            .order_by(DBMediaItem.date_created.desc().nullslast())
            .offset(offset)
            .limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [to_domain_media_item(r) for r in rows]

    def count_media_items(self) -> int:
        return int(self.session.execute(select(func.count()).select_from(DBMediaItem)).scalar_one())

    def find_video_candidates_for_thumbs(self, *, limit: int, regenerate: bool, missing: Literal["both", "either"] = "both") -> list[tuple[str, str, str]]:
        """
        Return up to `limit` tuples: (media_item_id, rel_dir, file_name)

        - regenerate=True  -> include all videos
        - regenerate=False -> include only videos missing assets per `missing`:
            • "both"   => missing BOTH thumb AND contact_sheet (current default)
            • "either" => missing EITHER thumb OR contact_sheet
        """
        MI = DBMediaItem
        MA = DBMediaAsset

        base = select(
            MI.id,
            MI.media_folder,
            MI.identity_name,
            MI.video_ext,
        ).where(MI.kind == MediaKind.video)

        if regenerate:
            stmt = base.order_by(MI.date_created.desc().nullslast()).limit(limit)
        else:
            Thumb = aliased(MA)
            Sheet = aliased(MA)

            stmt = (
                base
                .outerjoin(
                    Thumb,
                    and_(
                        Thumb.media_item_id == MI.id,
                        Thumb.kind == AssetKind.thumb,  # adjust if enum differs
                    ),
                )
                .outerjoin(
                    Sheet,
                    and_(
                        Sheet.media_item_id == MI.id,
                        Sheet.kind == AssetKind.contact_sheet,  # adjust if needed
                    ),
                )
            )
            if missing == "either":
                stmt = stmt.where(or_(Thumb.id.is_(None), Sheet.id.is_(None)))
            else:  # "both"
                stmt = stmt.where(and_(Thumb.id.is_(None), Sheet.id.is_(None)))
            stmt = stmt.order_by(MI.date_created.desc().nullslast()).limit(limit)


        rows: List[Tuple[str, str, str, str]] = self.session.execute(stmt).all()
        out: list[tuple[str, str, str]] = []
        for (mid, folder, name, ext) in rows:
            rel_dir = f"{folder}/{name}"
            file_name = f"{name}.{ext}"
            out.append((str(mid), rel_dir, file_name))
        return out

    def media_file_exists(self, media_root, rel_dir: str, file_name: str) -> bool:
        from pathlib import Path
        return (media_root / rel_dir / file_name).exists()

