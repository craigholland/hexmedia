from __future__ import annotations
from http import HTTPStatus
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from hexmedia.services.api.deps import transactional_session
from hexmedia.services.schemas.media import (
    MediaItemCreate, MediaItemRead, MediaItemPatch,
)
from hexmedia.services.mappers.media_item import (
    to_domain_from_create, to_read_schema, apply_patch_to_domain,
)
from hexmedia.database.models.media import MediaItem as DBMediaItem
from hexmedia.database.repos.media_repo import SqlAlchemyMediaRepo     # mutations
from hexmedia.database.repos.media_query import MediaQueryRepo         # queries
from hexmedia.domain.entities.media_item import MediaIdentity

router = APIRouter(prefix="/api/media-items", tags=["media-items"])

@router.post("", response_model=MediaItemRead, status_code=HTTPStatus.CREATED)
def create_media_item(payload: MediaItemCreate, session: Session = Depends(transactional_session)) -> MediaItemRead:
    repo = SqlAlchemyMediaRepo(db=session)
    try:
        domain_item = to_domain_from_create(payload)
        created = repo.create_media_item(domain_item)  # returns Domain
        return to_read_schema(created)
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e.orig))
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))

@router.get("/{item_id}", response_model=MediaItemRead)
def get_media_item(item_id: UUID = Path(...), session: Session = Depends(transactional_session)) -> MediaItemRead:
    q = MediaQueryRepo(session=session)
    found = q.get_by_id(item_id)
    if not found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    return to_read_schema(found)

@router.get("/by-identity", response_model=MediaItemRead)
def get_media_item_by_identity(
    media_folder: str = Query(...),
    identity_name: str = Query(...),
    video_ext: str = Query(...),
    session: Session = Depends(transactional_session),
) -> MediaItemRead:
    q = MediaQueryRepo(session=session)
    identity = MediaIdentity(media_folder=media_folder, identity_name=identity_name, video_ext=video_ext)
    found = q.get_by_identity(identity)
    if not found:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    return to_read_schema(found)

@router.get("", response_model=List[MediaItemRead])
def list_media_items(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(transactional_session),
) -> List[MediaItemRead]:
    # If you add a list method to MediaQueryRepo, use it; for now, simple scan:
    q = MediaQueryRepo(session=session)
    # Example naive list:
    from sqlalchemy import select
    rows = session.execute(
        select(DBMediaItem)  # type: ignore[name-defined]
        .order_by(DBMediaItem.date_created.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    # Convert via shared mapper then to read schema
    from hexmedia.database.repos._mapping import to_domain_media_item
    domain_rows = [to_domain_media_item(r) for r in rows]
    return [to_read_schema(r) for r in domain_rows]

@router.patch("/{item_id}", response_model=MediaItemRead)
def patch_media_item(item_id: UUID, payload: MediaItemPatch, session: Session = Depends(transactional_session)) -> MediaItemRead:
    repo = SqlAlchemyMediaRepo(db=session)
    current = repo.get_by_id(item_id)
    if not current:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="MediaItem not found")
    updated = apply_patch_to_domain(current, payload)
    try:
        saved = repo.update_media_item(updated)
        return to_read_schema(saved)
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=HTTPStatus.CONFLICT, detail=str(e.orig))

@router.delete("/{item_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_media_item(item_id: UUID, session: Session = Depends(transactional_session)) -> None:
    repo = SqlAlchemyMediaRepo(db=session)
    repo.delete_media_item(item_id)
