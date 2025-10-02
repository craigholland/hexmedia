from __future__ import annotations
from http import HTTPStatus
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from sqlalchemy.orm import Session

from hexmedia.services.api.deps import transactional_session
from hexmedia.database.repos.people_repo import SqlAlchemyPeopleRepo
from hexmedia.services.schemas.people import (
    PersonRead, PersonCreate, PersonUpdate, PersonLinkPayload
)

router = APIRouter(prefix="/api/people", tags=["people"])

# ---------- People (CRUD) ----------

@router.get("", response_model=List[PersonRead])
def search_people(
    q: str = Query("", description="case-insensitive substring"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(transactional_session),
) -> List[PersonRead]:
    repo = SqlAlchemyPeopleRepo(db)
    rows = repo.search(q, limit=limit)
    return [PersonRead.model_validate(r) for r in rows]


@router.get("/id/{person_id}", response_model=PersonRead)
def get_person(
    person_id: UUID = Path(...),
    db: Session = Depends(transactional_session),
) -> PersonRead:
    repo = SqlAlchemyPeopleRepo(db)
    obj = repo.get(person_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Person not found")
    return PersonRead.model_validate(obj)


@router.post("", response_model=PersonRead, status_code=HTTPStatus.CREATED)
def create_person(
    payload: PersonCreate,
    db: Session = Depends(transactional_session),
) -> PersonRead:
    repo = SqlAlchemyPeopleRepo(db)
    obj = repo.create(display_name=payload.name, normalized_name=payload.aka)
    db.flush(); db.refresh(obj)
    return PersonRead.model_validate(obj)


@router.patch("/id/{person_id}", response_model=PersonRead)
def update_person(
    person_id: UUID,
    payload: PersonUpdate,
    db: Session = Depends(transactional_session),
) -> PersonRead:
    repo = SqlAlchemyPeopleRepo(db)
    try:
        obj = repo.update(person_id, display_name=payload.name, normalized_name=payload.aka)
        db.flush(); db.refresh(obj)
    except ValueError:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Person not found")
    return PersonRead.model_validate(obj)


@router.delete("/id/{person_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_person(
    person_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    repo = SqlAlchemyPeopleRepo(db)
    repo.delete(person_id)
    db.flush()

# ---------- Links (Media <-> People) ----------

@router.get("/by-media/{media_item_id}", response_model=List[PersonRead])
def list_people_for_media(
    media_item_id: UUID = Path(...),
    db: Session = Depends(transactional_session),
) -> List[PersonRead]:
    repo = SqlAlchemyPeopleRepo(db)
    rows = repo.list_by_media(media_item_id)
    return [PersonRead.model_validate(r) for r in rows]


@router.post("/{person_id}/link/{media_item_id}", status_code=HTTPStatus.NO_CONTENT)
def link_person_to_media(
    person_id: UUID,
    media_item_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    repo = SqlAlchemyPeopleRepo(db)
    try:
        repo.link(media_item_id=media_item_id, person_id=person_id)
        db.flush()
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))


@router.delete("/{person_id}/link/{media_item_id}", status_code=HTTPStatus.NO_CONTENT)
def unlink_person_from_media(
    person_id: UUID,
    media_item_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    repo = SqlAlchemyPeopleRepo(db)
    repo.unlink(media_item_id=media_item_id, person_id=person_id)
    db.flush()

# (Optional) Body-based link/unlink endpoints)

@router.post("/link", status_code=HTTPStatus.NO_CONTENT)
def link_person_to_media_body(
    payload: PersonLinkPayload = Body(...),
    db: Session = Depends(transactional_session),
) -> None:
    repo = SqlAlchemyPeopleRepo(db)
    try:
        repo.link(media_item_id=payload.media_item_id, person_id=payload.person_id)
        db.flush()
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))


@router.post("/unlink", status_code=HTTPStatus.NO_CONTENT)
def unlink_person_from_media_body(
    payload: PersonLinkPayload = Body(...),
    db: Session = Depends(transactional_session),
) -> None:
    repo = SqlAlchemyPeopleRepo(db)
    repo.unlink(media_item_id=payload.media_item_id, person_id=payload.person_id)
    db.flush()
