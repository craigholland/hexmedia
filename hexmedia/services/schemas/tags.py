from __future__ import annotations
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Tag
class TagBase(BaseModel):
    name: str
    slug: str
    group_path: Optional[str]
    parent_path: Optional[str]
    description: Optional[str]

class TagCreate(TagBase):
    group_path: Optional[str]
    parent_path: Optional[str]

class TagUpdate(BaseModel):
    name: Optional[str] = None
    group_path: Optional[str]
    parent_path: Optional[str]
    description: Optional[str]

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
    children: List["TagGroupNode"] = []

    model_config = {"from_attributes": True}

TagGroupNode.model_rebuild()

class TagGroupCreate(BaseModel):
    key: str
    display_name: Optional[str] = None
    cardinality: Optional[str] = "multi"
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    parent_path: Optional[str] = None

class TagGroupMove(BaseModel):
    new_parent_id: Optional[UUID] = None
    new_parent_path: Optional[str] = None