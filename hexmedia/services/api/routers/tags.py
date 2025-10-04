from __future__ import annotations

from http import HTTPStatus
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from hexmedia.database.repos.tag_repo import TagRepo
from hexmedia.database.models.taxonomy import Tag, TagGroup
from hexmedia.domain.enums.cardinality import Cardinality
from hexmedia.services.schemas import (
    TagCreate,
    TagRead,
    TagUpdate,
    TagGroupCreate,
    TagGroupMove,
    TagGroupNode
)
from hexmedia.services.api.deps import get_db, transactional_session
from hexmedia.common.settings import get_settings

cfg = get_settings()
router = APIRouter(prefix=f"{cfg.api.prefix}/tags", tags=["tags"])

def _to_out(t: Tag) -> TagRead:
    return TagRead.model_validate(t)

@router.get("/groups", response_model=List[TagGroupNode])
def list_tag_groups_alias(db: Session = Depends(get_db)):
    return tag_group_tree(db)

def _resolve_ids_from_paths(db: Session, payload: TagCreate | TagUpdate):
    # group_id from group_path
    if getattr(payload, "group_id", None) is None and getattr(payload, "group_path", None):
        grp = db.query(TagGroup).filter(TagGroup.path == payload.group_path).one_or_none()
        if not grp:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Invalid group_path")
        payload.group_id = grp.id  # type: ignore[attr-defined]
    # parent_id from parent_path
    if getattr(payload, "parent_id", None) is None and getattr(payload, "parent_path", None):
        parent = db.query(Tag).filter(Tag.path == payload.parent_path).one_or_none()
        if not parent:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Invalid parent_path")
        payload.parent_id = parent.id  # type: ignore[attr-defined]

@router.post("", response_model=TagRead, status_code=HTTPStatus.CREATED)
def create_tag(payload: TagCreate, db: Session = Depends(transactional_session)) -> TagRead:
    # If a group_path is provided in the BODY, resolve it to group_id
    data = payload.model_dump()
    gpath = data.pop("group_path", None)
    ppath = data.pop("parent_path", None)

    if gpath:
        grp = db.query(TagGroup).filter(TagGroup.path == gpath).one_or_none()
        if not grp:
            raise HTTPException(status_code=400, detail="Invalid group_path")
        data["group_id"] = grp.id

    # (Optional) If you support parent_path, resolve it similarly to parent_id here

    obj = Tag(**data)
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return _to_out(obj)

@router.get("/{tag_id}", response_model=TagRead)
def get_tag(tag_id: UUID, db: Session = Depends(get_db)) -> TagRead:
    obj = db.get(Tag, tag_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Tag not found")
    return TagRead.model_validate(obj)

@router.get("", response_model=List[TagRead])
def list_tags(
    q: Optional[str] = Query(None),
    group_id: Optional[UUID] = Query(None),
    group_path: Optional[str] = Query(None),
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[TagRead]:
    stmt = select(Tag)
    if q:
        stmt = stmt.where(Tag.name.ilike(f"%{q}%"))
    if group_id:
        stmt = stmt.where(Tag.group_id == group_id)
    elif group_path:
        stmt = stmt.join(TagGroup, Tag.group_id == TagGroup.id).where(TagGroup.path == group_path)
    rows = db.execute(stmt.order_by(Tag.name.asc()).limit(limit)).scalars().all()
    return [_to_out(r) for r in rows]

@router.patch("/{tag_id}", response_model=TagRead)
def patch_tag(tag_id: UUID, payload: TagUpdate, db: Session = Depends(transactional_session)) -> TagRead:
    obj = db.get(Tag, tag_id)
    if not obj:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Tag not found")
    _resolve_ids_from_paths(db, payload)
    for k, v in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(obj, k, v)
    db.flush(); db.refresh(obj)
    return _to_out(obj)

@router.delete("/{tag_id}", status_code=HTTPStatus.NO_CONTENT)
def delete_tag(tag_id: UUID, db: Session = Depends(transactional_session)) -> None:
    obj = db.get(Tag, tag_id)
    if not obj:
        return
    db.delete(obj)
    # transactional_session will commit

@router.get("/tag-groups/tree", response_model=List[TagGroupNode])
def tag_group_tree(db: Session = Depends(get_db)) -> List[TagGroupNode]:
    repo = TagRepo(db)
    rows = repo.list_group_tree()
    by_id = {g.id: TagGroupNode.model_validate(g) for g in rows}
    roots: List[TagGroupNode] = []
    # reset children to avoid accumulation across calls
    for n in by_id.values():
        n.children = []
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
    obj = repo.create_group(
        key=payload.key,
        display_name=payload.display_name,
        cardinality=(payload.cardinality or Cardinality.MULTI.value),
        description=payload.description,
        parent_id=payload.parent_id,
        parent_path=payload.parent_path,
    )
    db.flush(); db.refresh(obj)
    return TagGroupNode.model_validate(obj)

@router.post("/tag-groups/{group_id}/move", response_model=TagGroupNode)
def move_tag_group(group_id: UUID, payload: TagGroupMove, db: Session = Depends(transactional_session)) -> TagGroupNode:
    repo = TagRepo(db)
    obj = repo.move_group(group_id, new_parent_id=payload.new_parent_id, new_parent_path=payload.new_parent_path)
    db.flush(); db.refresh(obj)
    return TagGroupNode.model_validate(obj)
