from __future__ import annotations

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict



# Person
class PersonBase(BaseModel):
    display_name: str
    normalized_name: Optional[str] = None

class PersonCreate(PersonBase):
    pass

class PersonUpdate(BaseModel):
    display_name: Optional[str] = None
    normalized_name: Optional[str] = None

class PersonRead(PersonBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
