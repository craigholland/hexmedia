from __future__ import annotations

from http import HTTPStatus
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hexmedia.database.models.media import MediaItem
from hexmedia.services.schemas import (
    MediaItemCreate, MediaItemRead, MediaItemUpdate
)
from hexmedia.services.api.deps import get_db

router = APIRouter()

def _to_out(mi: MediaItem) -> MediaItemRead:
    return MediaItemRead.model_validate(mi)

@router.post("", response_model=MediaItemRead, status_code=HTTPStatus.CREATED)
def create_media_item(payload: MediaItemCreate, db: Session = Depends(get_db)) -> MediaItemRead:
    obj = MediaItem(**payload.model_dump())
    db.add(obj)
    try:
        db.flush()  # get PK
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e.orig))
    db.refresh(obj)
    return _to_out(obj)

@router.get("/{item_id}", response_model=MediaItemRead)
def get_media_item(item_id: str = Path(...), db: Session = Depends(get_db)) -> MediaItemRead:
    obj = db.get(MediaItem, item_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    return _to_out(obj)

@router.get("/by-identity", response_model=MediaItemRead)
def get_media_item_by_identity(
    media_folder: str = Query(...),
    identity_name: str = Query(...),
    video_ext: str = Query(...),
    db: Session = Depends(get_db),
) -> MediaItemRead:
    stmt = (
        select(MediaItem)
        .where(
            and_(
                MediaItem.media_folder == media_folder,
                MediaItem.identity_name == identity_name,
                MediaItem.video_ext == video_ext,
            )
        )
        .limit(1)
    )
    obj = db.execute(stmt).scalars().first()
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    return _to_out(obj)

@router.get("", response_model=List[MediaItemRead])
def list_media_items(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[MediaItemRead]:
    rows = db.execute(select(MediaItem).order_by(MediaItem.date_created.desc()).offset(offset).limit(limit)).scalars().all()
    return [ _to_out(r) for r in rows ]

@router.patch("/{item_id}", response_model=MediaItemRead)
def patch_media_item(item_id: str, payload: MediaItemUpdate, db: Session = Depends(get_db)) -> MediaItemRead:
    obj = db.get(MediaItem, item_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e.orig))
    db.refresh(obj)
    return _to_out(obj)

@router.delete("/{item_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_media_item(item_id: str, db: Session = Depends(get_db)) -> None:
    obj = db.get(MediaItem, item_id)
    if not obj:
        # idempotent
        return
    db.delete(obj)
    db.flush()
