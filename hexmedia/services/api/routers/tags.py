from __future__ import annotations

from http import HTTPStatus
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from hexmedia.database.repos.tag_repo import TagRepo
from hexmedia.database.models.taxonomy import Tag
from hexmedia.services.schemas import (
    TagCreate,
    TagRead,
    TagUpdate,
    TagGroupCreate,
    TagGroupMove,
    TagGroupNode
)
from hexmedia.services.api.deps import get_db, transactional_session

router = APIRouter()

def _to_out(t: Tag) -> TagRead:
    return TagRead.model_validate(t)

@router.post("", response_model=TagRead, status_code=HTTPStatus.CREATED)
def create_tag(payload: TagCreate, group_path: Optional[str], db: Session = Depends(get_db)) -> TagRead:
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

@router.get("/tag-groups/tree", response_model=List[TagGroupNode])
def tag_group_tree(db: Session = Depends(transactional_session)) -> List[TagGroupNode]:
    repo = TagRepo(db)
    rows = repo.list_group_tree()

    # Build adjacency in memory
    by_id = {g.id: TagGroupNode.model_validate(g) for g in rows}
    roots: List[TagGroupNode] = []
    for g in rows:
        node = by_id[g.id]
        if g.parent_id and g.parent_id in by_id:
            by_id[g.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots

@router.post("/tag-groups", response_model=TagGroupNode, status_code=HTTPStatus.CREATED)
def create_tag_group(payload: TagGroupCreate, db: Session = Depends(transactional_session)) -> TagGroupNode:
    repo = TagRepo(db)
    try:
        obj = repo.create_group(
            key=payload.key,
            display_name=payload.display_name,
            cardinality=payload.cardinality or "multi",
            description=payload.description,
            parent_id=payload.parent_id,
            parent_path=payload.parent_path,
        )
        db.flush(); db.refresh(obj)
        return TagGroupNode.model_validate(obj)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))

@router.post("/tag-groups/{group_id}/move", response_model=TagGroupNode)
def move_tag_group(group_id: UUID, payload: TagGroupMove, db: Session = Depends(transactional_session)) -> TagGroupNode:
    repo = TagRepo(db)
    try:
        obj = repo.move_group(group_id, new_parent_id=payload.new_parent_id, new_parent_path=payload.new_parent_path)
        db.flush(); db.refresh(obj)
        return TagGroupNode.model_validate(obj)
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))