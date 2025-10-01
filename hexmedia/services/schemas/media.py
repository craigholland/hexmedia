# hexmedia/services/schemas/media.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from hexmedia.domain.enums.media_kind import MediaKind


# ---------- Identity DTOs (nested) ----------
class MediaIdentityIn(BaseModel):
    media_folder: str
    identity_name: str
    video_ext: str


class MediaIdentityOut(MediaIdentityIn):
    pass


# ---------- Shared base (kept) ----------
class MediaItemBase(BaseModel):
    kind: MediaKind = MediaKind.video

    # file stats / tech
    size_bytes: int = Field(0, ge=0)
    created_ts: Optional[datetime] = None     # if server-managed, keep only on Read
    modified_ts: Optional[datetime] = None

    hash_sha256: Optional[str] = None
    phash: Optional[int] = None

    duration_sec: Optional[int] = Field(None, ge=0)
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    fps: Optional[float] = Field(None, ge=0)
    bitrate: Optional[int] = Field(None, ge=0)
    codec_video: Optional[str] = None
    codec_audio: Optional[str] = None
    container: Optional[str] = None
    aspect_ratio: Optional[str] = None
    language: Optional[str] = None
    has_subtitles: bool = False

    # curation
    title: Optional[str] = None
    release_year: Optional[int] = Field(None, ge=1800, le=9999)
    source: Optional[str] = None
    watched: bool = False
    favorite: bool = False
    last_played_at: Optional[datetime] = None

    # provenance
    data_origin: Optional[str] = None

    model_config = ConfigDict(use_enum_values=False)


# ---------- Create / Patch / Read ----------
class MediaItemCreate(MediaItemBase):
    # identity is nested (required on create)
    identity: MediaIdentityIn


class MediaItemPatch(BaseModel):
    # identity is immutable via PATCH by design
    kind: Optional[MediaKind] = None

    size_bytes: Optional[int] = Field(None, ge=0)
    hash_sha256: Optional[str] = None
    phash: Optional[int] = None

    duration_sec: Optional[int] = Field(None, ge=0)
    width: Optional[int] = Field(None, ge=0)
    height: Optional[int] = Field(None, ge=0)
    fps: Optional[float] = Field(None, ge=0)
    bitrate: Optional[int] = Field(None, ge=0)
    codec_video: Optional[str] = None
    codec_audio: Optional[str] = None
    container: Optional[str] = None
    aspect_ratio: Optional[str] = None
    language: Optional[str] = None
    has_subtitles: Optional[bool] = None

    title: Optional[str] = None
    release_year: Optional[int] = Field(None, ge=1800, le=9999)
    source: Optional[str] = None
    watched: Optional[bool] = None
    favorite: Optional[bool] = None
    last_played_at: Optional[datetime] = None

    data_origin: Optional[str] = None


class MediaItemRead(MediaItemBase):
    id: UUID
    identity: MediaIdentityOut

    date_created: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    # allow mapping from ORM/domain objects directly
    model_config = ConfigDict(from_attributes=True, use_enum_values=False)
