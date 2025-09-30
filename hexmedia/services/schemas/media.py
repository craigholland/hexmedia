from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from hexmedia.domain.enums.media_kind import MediaKind

class MediaItemBase(BaseModel):
    kind: MediaKind
    media_folder: str
    identity_name: str
    video_ext: str

    size_bytes: int = 0
    created_ts: Optional[datetime] = None
    modified_ts: Optional[datetime] = None

    hash_sha256: Optional[str] = None
    phash: Optional[int] = None

    duration_sec: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None
    codec_video: Optional[str] = None
    codec_audio: Optional[str] = None
    container: Optional[str] = None
    aspect_ratio: Optional[str] = None
    language: Optional[str] = None
    has_subtitles: bool = False

    title: Optional[str] = None
    release_year: Optional[int] = None
    source: Optional[str] = None
    watched: bool = False
    favorite: bool = False
    last_played_at: Optional[datetime] = None

    # provenance
    data_origin: Optional[str] = None

    model_config = ConfigDict(use_enum_values=False)

class MediaItemCreate(MediaItemBase):
    pass

class MediaItemUpdate(BaseModel):
    kind: Optional[MediaKind] = None
    media_folder: Optional[str] = None
    identity_name: Optional[str] = None
    video_ext: Optional[str] = None

    size_bytes: Optional[int] = None
    created_ts: Optional[datetime] = None
    modified_ts: Optional[datetime] = None

    hash_sha256: Optional[str] = None
    phash: Optional[int] = None

    duration_sec: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None
    codec_video: Optional[str] = None
    codec_audio: Optional[str] = None
    container: Optional[str] = None
    aspect_ratio: Optional[str] = None
    language: Optional[str] = None
    has_subtitles: Optional[bool] = None

    title: Optional[str] = None
    release_year: Optional[int] = None
    source: Optional[str] = None
    watched: Optional[bool] = None
    favorite: Optional[bool] = None
    last_played_at: Optional[datetime] = None

    data_origin: Optional[str] = None

class MediaItemRead(MediaItemBase):
    id: UUID
    date_created: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
