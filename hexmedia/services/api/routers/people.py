# hexmedia/services/api/routers/people.py
from __future__ import annotations

from http import HTTPStatus
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from hexmedia.common.settings import get_settings
from hexmedia.database.models.person import Person as DBPerson, PersonAlias as DBAlias, PersonAliasLink as DBAliasLink
from hexmedia.services.api.deps import transactional_session
from hexmedia.services.schemas.people import (
    PersonCreate, PersonUpdate, PersonRead,
    PersonAliasCreate, PersonAliasRead
)

cfg = get_settings()
router = APIRouter(prefix=f"{cfg.api.prefix}/people", tags=["people"])


# ---- helpers ----

def _normalize(s: str) -> str:
    # best-effort normalization: lowercase + collapse whitespace
    return " ".join((s or "").lower().split())


def _person_or_404(db: Session, person_id: UUID) -> DBPerson:
    obj = db.get(DBPerson, person_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Person not found")
    return obj


# ---- CRUD ----

@router.get("", response_model=List[PersonRead])
def search_people(
    q: str = Query("", description="Case-insensitive substring (trigram-accelerated)"),
    limit: int = Query(25, ge=1, le=200),
    db: Session = Depends(transactional_session),
) -> List[PersonRead]:
    qn = _normalize(q)
    if not qn:
        stmt = select(DBPerson).order_by(DBPerson.display_name.asc()).limit(limit)
    else:
        # trigram-friendly LIKE against display_name (normalized index also exists)
        from sqlalchemy import func
        stmt = (
            select(DBPerson)
            .where(func.lower(DBPerson.display_name).like(f"%{qn}%"))
            .order_by(DBPerson.display_name.asc())
            .limit(limit)
        )
    rows = db.execute(stmt).scalars().all()
    return [PersonRead.model_validate(p) for p in rows]


@router.post("", response_model=PersonRead, status_code=HTTPStatus.CREATED)
def create_person(
    payload: PersonCreate,
    db: Session = Depends(transactional_session),
) -> PersonRead:
    obj = DBPerson(
        display_name=payload.display_name,
        normalized_name=payload.normalized_name or _normalize(payload.display_name),
        notes=payload.notes,
        avatar_asset_id=payload.avatar_asset_id,
    )
    db.add(obj)
    db.flush()  # ensure id
    db.refresh(obj)
    return PersonRead.model_validate(obj)


@router.get("/{person_id}", response_model=PersonRead)
def get_person(
    person_id: UUID = Path(...),
    db: Session = Depends(transactional_session),
) -> PersonRead:
    obj = _person_or_404(db, person_id)
    return PersonRead.model_validate(obj)


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(
    person_id: UUID,
    payload: PersonUpdate,
    db: Session = Depends(transactional_session),
) -> PersonRead:
    obj = _person_or_404(db, person_id)

    if payload.display_name is not None:
        obj.display_name = payload.display_name
        # if normalized_name omitted, keep existing; caller can explicitly set it
        if payload.normalized_name is None:
            obj.normalized_name = _normalize(payload.display_name)

    if payload.normalized_name is not None:
        obj.normalized_name = payload.normalized_name

    if payload.notes is not None:
        obj.notes = payload.notes

    if payload.avatar_asset_id is not None:
        obj.avatar_asset_id = payload.avatar_asset_id

    db.flush()
    db.refresh(obj)
    return PersonRead.model_validate(obj)


@router.delete("/{person_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_person(
    person_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    obj = _person_or_404(db, person_id)
    db.delete(obj)
    # 204
    return None


# ---- Aliases ----

@router.get("/{person_id}/aliases", response_model=List[PersonAliasRead])
def list_person_aliases(
    person_id: UUID,
    db: Session = Depends(transactional_session),
) -> List[PersonAliasRead]:
    p = _person_or_404(db, person_id)
    # relationship is eager-selectin; model_validate handles it
    return [PersonAliasRead.model_validate(a) for a in (p.aliases or [])]


@router.post("/{person_id}/aliases", response_model=PersonAliasRead, status_code=HTTPStatus.CREATED)
def add_alias_to_person(
    person_id: UUID,
    payload: PersonAliasCreate,
    db: Session = Depends(transactional_session),
) -> PersonAliasRead:
    p = _person_or_404(db, person_id)
    norm = _normalize(payload.alias)

    # find or create global alias
    from sqlalchemy import select
    existing = db.execute(
        select(DBAlias).where(DBAlias.alias_normalized == norm).limit(1)
    ).scalars().first()

    if existing is None:
        existing = DBAlias(alias=payload.alias.strip(), alias_normalized=norm, notes=payload.notes)
        db.add(existing)
        db.flush()

    # link (idempotent)
    link_exists = db.execute(
        select(DBAliasLink).where(
            DBAliasLink.person_id == p.id,
            DBAliasLink.alias_id == existing.id,
        ).limit(1)
    ).scalars().first()

    if link_exists is None:
        db.add(DBAliasLink(person_id=p.id, alias_id=existing.id))

    db.flush()
    db.refresh(existing)
    return PersonAliasRead.model_validate(existing)


@router.delete("/{person_id}/aliases/{alias_id}", status_code=HTTPStatus.NO_CONTENT)
def remove_alias_link(
    person_id: UUID,
    alias_id: UUID,
    db: Session = Depends(transactional_session),
) -> None:
    _person_or_404(db, person_id)
    from sqlalchemy import delete
    db.execute(
        delete(DBAliasLink).where(
            DBAliasLink.person_id == person_id,
            DBAliasLink.alias_id == alias_id,
        )
    )
    # We purposely do NOT delete the alias record itself (it may be shared).
    return None