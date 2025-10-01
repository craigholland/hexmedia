from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict

# READ (base)
class PersonRead(BaseModel):
    id: UUID
    name: str
    aka: Optional[str] = None  # adjust if your model uses a different column
    model_config = ConfigDict(from_attributes=True)

# WRITE
class PersonCreate(BaseModel):
    name: str
    aka: Optional[str] = None

class PersonUpdate(BaseModel):
    name: Optional[str] = None
    aka: Optional[str] = None

# Linking payloads (if you prefer body payloads over params)
class PersonLinkPayload(BaseModel):
    person_id: UUID
    media_item_id: UUID
