from __future__ import annotations
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# Tag
class TagBase(BaseModel):
    name: str
    path: str
    is_deprecated: bool = False

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    is_deprecated: Optional[bool] = None

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