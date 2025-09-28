# hexmedia/domain/entities/media_item.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from hexmedia.domain.enums.media_kind import MediaKind


@dataclass(frozen=True)
class MediaIdentity:
    """
    Immutable identity triplet for a media item. This is the *only* thing
    needed to locate files on disk given a known media_root:

        <media_root>/<media_folder>/<identity_name>/<identity_name>.<video_ext>
        <media_root>/<media_folder>/<identity_name>/assets/...

    This class stays framework-free and does not build absolute paths.
    """
    media_folder: str
    identity_name: str
    video_ext: str

    def as_key(self) -> Tuple[str, str, str]:
        return (self.media_folder, self.identity_name, self.video_ext)

    def video_filename(self) -> str:
        return f"{self.identity_name}.{self.video_ext}"

    def rel_dir(self) -> str:
        # directory that contains the video and assets subdir
        return f"{self.media_folder}/{self.identity_name}"

    def video_rel_path(self) -> str:
        return f"{self.rel_dir()}/{self.video_filename()}"

    def assets_rel_dir(self) -> str:
        return f"{self.rel_dir()}/assets"


@dataclass
class MediaItem:
    """
    Core domain entity for a piece of media. Persistence concerns (DB IDs,
    timestamps) are optional and not required for in-memory use.

    Invariants that we keep here:
      - kind is a valid MediaKind
      - identity fields are non-empty
      - size and dimensions non-negative when provided
    More involved rules (e.g., "one asset per kind", "rating singleton")
    are enforced at the DB/policy layer to keep entities lean.
    """
    # Persistence (optional)
    id: Optional[UUID] = None
    date_created: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    data_origin: Optional[str] = None  # provenance note

    # Identity
    kind: MediaKind = MediaKind.video
    identity: MediaIdentity = None  # set in __post_init__

    # File stats / tech
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

    # Curation
    title: Optional[str] = None
    release_year: Optional[int] = None
    source: Optional[str] = None
    watched: bool = False
    favorite: bool = False
    last_played_at: Optional[datetime] = None

    # --- constructor args for identity (ergonomic) ---
    media_folder: Optional[str] = None
    identity_name: Optional[str] = None
    video_ext: Optional[str] = None

    def __post_init__(self):
        # Hydrate identity from convenience fields if caller passed them
        if self.identity is None:
            if not (self.media_folder and self.identity_name and self.video_ext):
                raise ValueError("MediaItem requires identity triplet: media_folder, identity_name, video_ext")
            self.identity = MediaIdentity(
                media_folder=self.media_folder,
                identity_name=self.identity_name,
                video_ext=self.video_ext,
            )
        # basic sanity checks
        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValueError("size_bytes must be >= 0")
        if self.width is not None and self.width < 0:
            raise ValueError("width must be >= 0")
        if self.height is not None and self.height < 0:
            raise ValueError("height must be >= 0")
        if self.duration_sec is not None and self.duration_sec < 0:
            raise ValueError("duration_sec must be >= 0")
        if self.bitrate is not None and self.bitrate < 0:
            raise ValueError("bitrate must be >= 0")

    # ---- Identity helpers -------------------------------------------------

    @property
    def media_folder(self) -> str:  # type: ignore[override]
        return self.identity.media_folder

    @media_folder.setter
    def media_folder(self, value: Optional[str]) -> None:  # ignore in dataclass init
        # no-op; dataclass injector uses this name; actual storage is in identity
        pass

    @property
    def identity_name(self) -> str:  # type: ignore[override]
        return self.identity.identity_name

    @identity_name.setter
    def identity_name(self, value: Optional[str]) -> None:
        pass

    @property
    def video_ext(self) -> str:  # type: ignore[override]
        return self.identity.video_ext

    @video_ext.setter
    def video_ext(self, value: Optional[str]) -> None:
        pass

    def identity_key(self) -> Tuple[str, str, str]:
        return self.identity.as_key()

    def video_rel_path(self) -> str:
        return self.identity.video_rel_path()

    def assets_rel_dir(self) -> str:
        return self.identity.assets_rel_dir()
