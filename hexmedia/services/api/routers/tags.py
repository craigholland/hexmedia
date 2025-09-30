from __future__ import annotations

from http import HTTPStatus
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from hexmedia.database.models.taxonomy import Tag
from hexmedia.services.schemas import TagCreate, TagRead, TagUpdate
from hexmedia.services.api.deps import get_db

router = APIRouter()

def _to_out(t: Tag) -> TagRead:
    return TagRead.model_validate(t)

@router.post("", response_model=TagRead, status_code=HTTPStatus.CREATED)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)) -> TagRead:
    obj = Tag(**payload.model_dump())
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return _to_out(obj)

@router.get("/{tag_id}", response_model=TagRead)
def get_tag(tag_id: str, db: Session = Depends(get_db)) -> TagRead:
    obj = db.get(Tag, tag_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Tag not found")
    return _to_out(obj)

@router.get("", response_model=List[TagRead])
def list_tags(q: str | None = Query(None), limit: int = 100, db: Session = Depends(get_db)) -> List[TagRead]:
    stmt = select(Tag)
    if q:
        stmt = stmt.where(Tag.name.ilike(f"%{q}%"))
    rows = db.execute(stmt.order_by(Tag.name.asc()).limit(limit)).scalars().all()
    return [ _to_out(r) for r in rows ]

@router.patch("/{tag_id}", response_model=TagRead)
def patch_tag(tag_id: str, payload: TagUpdate, db: Session = Depends(get_db)) -> TagRead:
    obj = db.get(Tag, tag_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Tag not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.flush()
    db.refresh(obj)
    return _to_out(obj)

@router.delete("/{tag_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_tag(tag_id: str, db: Session = Depends(get_db)) -> None:
    obj = db.get(Tag, tag_id)
    if not obj:
        return
    db.delete(obj)
    db.flush()
