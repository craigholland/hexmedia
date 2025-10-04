from __future__ import annotations
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from hexmedia.domain.enums.cardinality import Cardinality

# Tag
class TagBase(BaseModel):
    name: str
    slug: str
    group_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    group_path: Optional[str] = None
    parent_path: Optional[str] = None
    description: Optional[str] = None

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = None
    group_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    group_path: Optional[str] = None
    parent_path: Optional[str] = None
    description: Optional[str] = None

class TagRead(TagBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class TagGroupNode(BaseModel):
    id: UUID
    key: str
    display_name: str
    path: str
    depth: int
    cardinality: str
    children: List["TagGroupNode"] = Field(default_factory=list)

    model_config = {"from_attributes": True}

TagGroupNode.model_rebuild()

class TagGroupCreate(BaseModel):
    key: str
    display_name: Optional[str] = None
    cardinality: Optional[str] = Cardinality.MULTI.value
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    parent_path: Optional[str] = None

class TagGroupMove(BaseModel):
    new_parent_id: Optional[UUID] = None
    new_parent_path: Optional[str] = None
    
class TagGroupUpdate(BaseModel):
    # All optional so you can PATCH any subset of fields
    key: Optional[str] = None
    display_name: Optional[str] = None
    cardinality: Optional[str] = None     # e.g. "single" | "multi"
    description: Optional[str] = None
    parent_id: Optional[UUID] = None      # move under a new parent by id
    parent_path: Optional[str] = None     # 