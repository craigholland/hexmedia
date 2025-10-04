from __future__ import annotations

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hexmedia.common.settings import get_settings
from hexmedia.services.api.deps import transactional_session
from hexmedia.services.schemas.media_tags import MediaTagAttach, MediaTagRead
from hexmedia.database.models.taxonomy import Tag, TagGroup, MediaTag as MediaItemTag
from hexmedia.database.models.media import MediaItem
from hexmedia.domain.enums.cardinality import Cardinality

cfg = get_settings()

router = APIRouter(prefix=f"{cfg.api.prefix}/media-tags", tags=["media-tags"])

def _get_media_or_404(db: Session, media_id: UUID) -> MediaItem:
    obj = db.get(MediaItem, media_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Media item not found")
    return obj

def _get_tag_by_any(db: Session, payload: MediaTagAttach) -> Tag:
    if payload.tag_id:
        tag = db.get(Tag, payload.tag_id)
        if not tag:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Tag not found")
        return tag
    if payload.group_path and payload.tag_slug:
        # resolve group by path then tag by slug (adjust to your repo if you have helpers)
        grp = db.query(TagGroup).filter(TagGroup.path == payload.group_path).one_or_none()
        if not grp:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Invalid group_path")
        tag = db.query(Tag).filter(Tag.group_id == grp.id, Tag.slug == payload.tag_slug).one_or_none()
        if not tag:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Invalid tag_slug for group")
        return tag
    raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Provide tag_id or (group_path + tag_slug)")

@router.post("/media-items/{media_id}/tags", response_model=MediaTagRead, status_code=HTTPStatus.CREATED)
def attach_tag_to_media(
    media_id: UUID,
    payload: MediaTagAttach,
    db: Session = Depends(transactional_session),
) -> MediaTagRead:
    media = _get_media_or_404(db, media_id)
    tag = _get_tag_by_any(db, payload)

    # enforce group cardinality
    if tag.group_id:
        grp = db.get(TagGroup, tag.group_id)
        if grp and grp.cardinality == Cardinality.SINGLE:
            # remove any existing tag from the same group
            existing = (
                db.query(MediaItemTag)
                .join(Tag, MediaItemTag.tag_id == Tag.id)
                .filter(MediaItemTag.media_item_id == media.id, Tag.group_id == grp.id)
                .all()
            )
            for rel in existing:
                db.delete(rel)

    # create relation if not already present
    rel = (
        db.query(MediaItemTag)
        .filter(MediaItemTag.media_item_id == media.id, MediaItemTag.tag_id == tag.id)
        .one_or_none()
    )
    if not rel:
        rel = MediaItemTag(media_item_id=media.id, tag_id=tag.id)
        db.add(rel)

    db.flush()
    return MediaTagRead(media_item_id=media.id, tag_id=tag.id)

@router.delete("/media-items/{media_id}/tags/{tag_id}", status_code=HTTPStatus.NO_CONTENT)
def detach_tag_from_media(
    media_id: UUID,
    tag_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    _ = _get_media_or_404(db, media_id)
    rel = (
        db.query(MediaItemTag)
        .filter(MediaItemTag.media_item_id == media_id, MediaItemTag.tag_id == tag_id)
        .one_or_none()
    )
    if rel:
        db.delete(rel)
    # transactional_session will commit
