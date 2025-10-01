from __future__ import annotations

from http import HTTPStatus
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hexmedia.services.api.deps import transactional_session
from hexmedia.database.repos.media_asset_repo import SqlAlchemyMediaAssetRepo
from hexmedia.services.schemas.assets import (
    MediaAssetRead, MediaAssetCreate, MediaAssetUpdate
)

router = APIRouter()


@router.get("/by-media/{media_item_id}", response_model=List[MediaAssetRead])
def list_assets_for_media(
    media_item_id: UUID = Path(...),
    db: Session = Depends(transactional_session),
) -> List[MediaAssetRead]:
    repo = SqlAlchemyMediaAssetRepo(db)
    rows = repo.list_by_media(media_item_id)
    return [MediaAssetRead.model_validate(r) for r in rows]


@router.get("/{asset_id}", response_model=MediaAssetRead)
def get_asset(
    asset_id: UUID,
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
    repo = SqlAlchemyMediaAssetRepo(db)
    obj = repo.get(asset_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Asset not found")
    return MediaAssetRead.model_validate(obj)


@router.post("", response_model=MediaAssetRead, status_code=HTTPStatus.CREATED)
def create_asset(
    payload: MediaAssetCreate,
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
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
        # Likely uniqueness violation (media_item_id, kind)
        db.rollback()
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Asset of this kind already exists for the media item",
        ) from e
    return MediaAssetRead.model_validate(obj)


@router.put("/upsert", response_model=MediaAssetRead)
def upsert_asset(
    payload: MediaAssetCreate,  # same shape as create
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
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
    return MediaAssetRead.model_validate(obj)


@router.patch("/{asset_id}", response_model=MediaAssetRead)
def patch_asset(
    asset_id: UUID,
    payload: MediaAssetUpdate,
    db: Session = Depends(transactional_session),
) -> MediaAssetRead:
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
    return MediaAssetRead.model_validate(obj)


@router.delete("/{asset_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_asset(
    asset_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    repo = SqlAlchemyMediaAssetRepo(db)
    repo.delete(asset_id)
    db.flush()
