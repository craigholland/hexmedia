from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hexmedia.database.models.media import MediaAsset as DBMediaAsset
from hexmedia.domain.enums.asset_kind import AssetKind


class SqlAlchemyMediaAssetRepo:
    def __init__(self, session: Session) -> None:
        self.db = session

    # --------- Reads ---------

    def get(self, asset_id: UUID) -> Optional[DBMediaAsset]:
        return self.db.get(DBMediaAsset, asset_id)

    def list_by_media(self, media_item_id: UUID) -> List[DBMediaAsset]:
        stmt = (
            select(DBMediaAsset)
            .where(DBMediaAsset.media_item_id == media_item_id)
            .order_by(DBMediaAsset.kind.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def get_by_item_kind(self, media_item_id: UUID, kind: AssetKind) -> Optional[DBMediaAsset]:
        stmt = select(DBMediaAsset).where(
            and_(
                DBMediaAsset.media_item_id == media_item_id,
                DBMediaAsset.kind == kind,
            )
        ).limit(1)
        return self.db.execute(stmt).scalars().first()

    # --------- Writes ---------

    def create(
        self,
        *,
        media_item_id: UUID,
        kind: AssetKind,
        rel_path: str,
        width: int | None = None,
        height: int | None = None,
    ) -> DBMediaAsset:
        obj = DBMediaAsset(
            media_item_id=media_item_id,
            kind=kind,
            rel_path=rel_path,
            width=width,
            height=height,
        )
        self.db.add(obj)
        # let caller control flush/commit when used transactionally
        return obj

    def upsert(
        self,
        *,
        media_item_id: UUID,
        kind: AssetKind,
        rel_path: str,
        width: int | None = None,
        height: int | None = None,
    ) -> DBMediaAsset:
        existing = self.get_by_item_kind(media_item_id, kind)
        if existing:
            existing.rel_path = rel_path
            existing.width = width
            existing.height = height
            return existing
        return self.create(
            media_item_id=media_item_id,
            kind=kind,
            rel_path=rel_path,
            width=width,
            height=height,
        )

    def update(
        self,
        asset_id: UUID,
        *,
        rel_path: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> DBMediaAsset:
        obj = self.get(asset_id)
        if not obj:
            raise ValueError("Asset not found")
        if rel_path is not None:
            obj.rel_path = rel_path
        if width is not None:
            obj.width = width
        if height is not None:
            obj.height = height
        return obj

    def delete(self, asset_id: UUID) -> None:
        obj = self.get(asset_id)
        if not obj:
            return
        self.db.delete(obj)
