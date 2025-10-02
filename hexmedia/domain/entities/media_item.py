# hexmedia/domain/entities/media_item.py
from __future__ import annotations

from dataclasses import dataclass, asdict, InitVar
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from hexmedia.domain.enums.media_kind import MediaKind
from hexmedia.common.logging import get_logger

logger = get_logger()


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

    def as_dict(self):
        return asdict(self)


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

    Option B:
    ---------
    We accept an explicit MediaIdentity OR an InitVar triplet
    (media_folder_in, identity_name_in, video_ext_in) to hydrate identity.
    """

    # Persistence (optional)
    id: Optional[UUID] = None
    date_created: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    data_origin: Optional[str] = None  # provenance note

    # Identity
    kind: MediaKind = MediaKind.video
    identity: Optional[MediaIdentity] = None

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

    # --- InitVar triplet for ergonomic construction (kept OUT of dataclass fields) ---
    media_folder_in: InitVar[Optional[str]] = None
    identity_name_in: InitVar[Optional[str]] = None
    video_ext_in: InitVar[Optional[str]] = None

    def __post_init__(self, media_folder_in, identity_name_in, video_ext_in):
        # Hydrate identity from InitVars if not provided explicitly
        if self.identity is None:
            if media_folder_in and identity_name_in and video_ext_in:
                self.identity = MediaIdentity(
                    media_folder=str(media_folder_in),
                    identity_name=str(identity_name_in),
                    video_ext=str(video_ext_in),
                )
            else:
                raise ValueError(
                    "MediaItem requires identity (MediaIdentity) or the full triplet via "
                    "media_folder_in / identity_name_in / video_ext_in"
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

    # ---- Identity helpers (proxies) ----------------------------------------

    @property
    def media_folder(self) -> str:
        return self.identity.media_folder  # type: ignore[union-attr]

    @property
    def identity_name(self) -> str:
        return self.identity.identity_name  # type: ignore[union-attr]

    @property
    def video_ext(self) -> str:
        return self.identity.video_ext  # type: ignore[union-attr]

    def identity_key(self) -> Tuple[str, str, str]:
        return self.identity.as_key()  # type: ignore[union-attr]

    def video_rel_path(self) -> str:
        return self.identity.video_rel_path()  # type: ignore[union-attr]

    def assets_rel_dir(self) -> str:
        return self.identity.assets_rel_dir()  # type: ignore[union-attr]

    def as_dict(self):
        return asdict(self)
