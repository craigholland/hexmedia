from __future__ import annotations

from http import HTTPStatus
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hexmedia.common.settings import get_settings
from hexmedia.services.api.deps import transactional_session
from hexmedia.database.models.media import MediaItem as DBMediaItem
from hexmedia.database.repos.media_asset_repo import SqlAlchemyMediaAssetRepo
from hexmedia.services.schemas.assets import (
    MediaAssetRead, MediaAssetCreate, MediaAssetUpdate
)

router = APIRouter(prefix="/api/assets", tags=["assets"])

def _asset_url_for(
    *, cfg, item: DBMediaItem | None, rel_path: str
) -> str | None:
    """
    Build absolute URL if PUBLIC_MEDIA_URL is configured.
    rel_path is relative to the item's directory (usually 'assets/...').
    """
    if not item or not cfg.public_media_base_url:
        return None
    base = cfg.public_media_base_url.rstrip("/")
    rel_dir = f"{item.media_folder}/{item.identity_name}".strip("/")
    return f"{base}/{rel_dir}/{rel_path.lstrip('/')}"


@router.get("/by-media/{media_item_id}", response_model=List[MediaAssetRead])
def list_assets_for_media(
    media_item_id: UUID = Path(...),
    db: Session = Depends(transactional_session),
) -> List[MediaAssetRead]:
    cfg = get_settings()
    repo = SqlAlchemyMediaAssetRepo(db)
    rows = repo.list_by_media(media_item_id)

    # fetch parent once
    parent = db.get(DBMediaItem, media_item_id)

    out = []
    for r in rows:
        dto = MediaAssetRead.model_validate(r)
        dto.url = _asset_url_for(cfg=cfg, item=parent, rel_path=dto.rel_path)
        out.append(dto)
    return out


@router.get("/{asset_id}", response_model=MediaAssetRead)
def get_asset(
    asset_id: UUID,
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
    cfg = get_settings()
    repo = SqlAlchemyMediaAssetRepo(db)
    obj = repo.get(asset_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Asset not found")
    dto = MediaAssetRead.model_validate(obj)
    parent = db.get(DBMediaItem, obj.media_item_id)
    dto.url = _asset_url_for(cfg=cfg, item=parent, rel_path=dto.rel_path)
    return dto


@router.post("", response_model=MediaAssetRead, status_code=HTTPStatus.CREATED)
def create_asset(
    payload: MediaAssetCreate,
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
    cfg = get_settings()
    repo = SqlAlchemyMediaAssetRepo(db)
    try:
        obj = repo.create(
            media_item_id=payload.media_item_id,
            kind=payload.kind,
            rel_path=payload.rel_path,
            width=payload.width,
            height=payload.height,
        )
        db.flush()
        db.refresh(obj)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Asset of this kind already exists for the media item",
        ) from e
    dto = MediaAssetRead.model_validate(obj)
    parent = db.get(DBMediaItem, obj.media_item_id)
    dto.url = _asset_url_for(cfg=cfg, item=parent, rel_path=dto.rel_path)
    return dto



@router.put("/upsert", response_model=MediaAssetRead)
def upsert_asset(
    payload: MediaAssetCreate,
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
    cfg = get_settings()
    repo = SqlAlchemyMediaAssetRepo(db)
    obj = repo.upsert(
        media_item_id=payload.media_item_id,
        kind=payload.kind,
        rel_path=payload.rel_path,
        width=payload.width,
        height=payload.height,
    )
    db.flush()
    db.refresh(obj)
    dto = MediaAssetRead.model_validate(obj)
    parent = db.get(DBMediaItem, obj.media_item_id)
    dto.url = _asset_url_for(cfg=cfg, item=parent, rel_path=dto.rel_path)
    return dto


@router.patch("/{asset_id}", response_model=MediaAssetRead)
def patch_asset(
    asset_id: UUID,
    payload: MediaAssetUpdate,
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
    cfg = get_settings()
    repo = SqlAlchemyMediaAssetRepo(db)
    try:
        obj = repo.update(
            asset_id,
            rel_path=payload.rel_path,
            width=payload.width,
            height=payload.height,
        )
        db.flush()
        db.refresh(obj)
    except ValueError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Asset not found")
    dto = MediaAssetRead.model_validate(obj)
    parent = db.get(DBMediaItem, obj.media_item_id)
    dto.url = _asset_url_for(cfg=cfg, item=parent, rel_path=dto.rel_path)
    return dto



@router.delete("/id/{asset_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_asset(
    asset_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    repo = SqlAlchemyMediaAssetRepo(db)
    repo.delete(asset_id)
    db.flush()
