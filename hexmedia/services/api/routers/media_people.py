# hexmedia/services/api/routers/media_people.py
from __future__ import annotations

from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from hexmedia.common.settings import get_settings
from hexmedia.database.models.media import MediaItem as DBMediaItem
from hexmedia.database.models.person import Person as DBPerson, MediaPerson as DBMediaPerson
from hexmedia.services.api.deps import transactional_session
from hexmedia.services.schemas.people import MediaPersonLinkRead

cfg = get_settings()
router = APIRouter(prefix=f"{cfg.api.prefix}/media-items", tags=["people-links"])


def _media_or_404(db: Session, media_id: UUID) -> DBMediaItem:
    obj = db.get(DBMediaItem, media_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Media item not found")
    return obj


def _person_or_404(db: Session, person_id: UUID) -> DBPerson:
    obj = db.get(DBPerson, person_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Person not found")
    return obj


@router.post("/{media_id}/people/{person_id}", response_model=MediaPersonLinkRead, status_code=HTTPStatus.CREATED)
def link_person_to_media(
    media_id: UUID = Path(...),
    person_id: UUID = Path(...),
    db: Session = Depends(transactional_session),
) -> MediaPersonLinkRead:
    m = _media_or_404(db, media_id)
    p = _person_or_404(db, person_id)

    # idempotent link (unique constraint on pair)
    from sqlalchemy import select, and_
    link = db.execute(
        select(DBMediaPerson).where(
            and_(
                DBMediaPerson.media_item_id == m.id,
                DBMediaPerson.person_id == p.id,
            )
        ).limit(1)
    ).scalars().first()
    if link is None:
        link = DBMediaPerson(media_item_id=m.id, person_id=p.id)  # role defaults to 'actor'
        db.add(link)
        db.flush()
        db.refresh(link)

    return MediaPersonLinkRead.model_validate(link)


@router.delete("/{media_id}/people/{person_id}", status_code=HTTPStatus.NO_CONTENT)
def unlink_person_from_media(
    media_id: UUID,
    person_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    _media_or_404(db, media_id)
    _person_or_404(db, person_id)
    from sqlalchemy import delete, and_
    db.execute(
        delete(DBMediaPerson).where(
            and_(
                DBMediaPerson.media_item_id == media_id,
                DBMediaPerson.person_id == person_id,
            )
        )
    )
    return None
