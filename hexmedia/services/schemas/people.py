# hexmedia/services/schemas/people.py
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hexmedia.domain.enums import PersonRole


# ---------- Aliases ----------

class PersonAliasCreate(BaseModel):
    alias: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None


class PersonAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alias: str
    alias_normalized: str
    notes: Optional[str] = None


# ---------- Person ----------

class PersonBase(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)
    normalized_name: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None
    avatar_asset_id: Optional[UUID] = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=255)
    normalized_name: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None
    avatar_asset_id: Optional[UUID] = None


class PersonRead(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    aliases: List[PersonAliasRead] = []


# ---------- Media <-> Person link ----------

class MediaPersonLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    media_item_id: UUID
    person_id: UUID
    role: PersonRole
