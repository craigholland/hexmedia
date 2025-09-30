from __future__ import annotations

from http import HTTPStatus
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from hexmedia.database.models.taxonomy import Person
from hexmedia.services.schemas import PersonCreate, PersonRead, PersonUpdate
from hexmedia.services.api.deps import get_db

router = APIRouter()

def _to_out(p: Person) -> PersonRead:
    return PersonRead.model_validate(p)

@router.post("", response_model=PersonRead, status_code=HTTPStatus.CREATED)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> PersonRead:
    obj = Person(**payload.model_dump())
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return _to_out(obj)

@router.get("/{person_id}", response_model=PersonRead)
def get_person(person_id: str, db: Session = Depends(get_db)) -> PersonRead:
    obj = db.get(Person, person_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Person not found")
    return _to_out(obj)

@router.get("", response_model=List[PersonRead])
def list_people(q: str | None = Query(None), limit: int = 100, db: Session = Depends(get_db)) -> List[PersonRead]:
    stmt = select(Person)
    if q:
        stmt = stmt.where(Person.display_name.ilike(f"%{q}%"))
    rows = db.execute(stmt.order_by(Person.display_name.asc()).limit(limit)).scalars().all()
    return [ _to_out(r) for r in rows ]

@router.patch("/{person_id}", response_model=PersonRead)
def patch_person(person_id: str, payload: PersonUpdate, db: Session = Depends(get_db)) -> PersonRead:
    obj = db.get(Person, person_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Person not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.flush()
    db.refresh(obj)
    return _to_out(obj)

@router.delete("/{person_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_person(person_id: str, db: Session = Depends(get_db)) -> None:
    obj = db.get(Person, person_id)
    if not obj:
        return
    db.delete(obj)
    db.flush()
