# hexmedia/database/repos/media_asset_repo.py
from __future__ import annotations
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from hexmedia.database.models.media import MediaAsset as DBMediaAsset, MediaItem as DBMediaItem
from hexmedia.domain.entities.media_asset import MediaAsset as DomainAsset  # if you have it
from hexmedia.domain.enums.asset_kind import AssetKind

class SqlAlchemyMediaAssetWriter:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_asset(
        self,
        *,
        media_item_id: str | UUID,
        kind: str | AssetKind,
        rel_path: str,
        width: Optional[int],
        height: Optional[int],
    ) -> None:
        # normalize
        mid = media_item_id
        akind = kind if isinstance(kind, AssetKind) else AssetKind(kind)

        # try fetch
        row = self.session.execute(
            select(DBMediaAsset).where(
                DBMediaAsset.media_item_id == mid,
                DBMediaAsset.kind == akind,
            )
        ).scalars().first()

        if row:
            row.rel_path = rel_path
            row.width = width
            row.height = height
        else:
            self.session.add(
                DBMediaAsset(
                    media_item_id=mid,
                    kind=akind,
                    rel_path=rel_path,
                    width=width,
                    height=height,
                )
            )
        # no commit here; request-scoped transaction will handle it
