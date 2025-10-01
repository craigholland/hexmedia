# hexmedia/services/mappers/media_item_mapper.py
from __future__ import annotations

from hexmedia.domain.entities.media_item import MediaItem, MediaIdentity
from hexmedia.services.schemas.media import (
    MediaItemCreate, MediaItemPatch, MediaItemRead,
    MediaIdentityOut,
)

def to_domain_from_create(s: MediaItemCreate) -> MediaItem:
    return MediaItem(
        kind=s.kind,
        media_folder=s.identity.media_folder,
        identity_name=s.identity.identity_name,
        video_ext=s.identity.video_ext,

        size_bytes=s.size_bytes,
        created_ts=s.created_ts,
        modified_ts=s.modified_ts,

        hash_sha256=s.hash_sha256,
        phash=s.phash,

        duration_sec=s.duration_sec,
        width=s.width,
        height=s.height,
        fps=s.fps,
        bitrate=s.bitrate,
        codec_video=s.codec_video,
        codec_audio=s.codec_audio,
        container=s.container,
        aspect_ratio=s.aspect_ratio,
        language=s.language,
        has_subtitles=bool(s.has_subtitles),

        title=s.title,
        release_year=s.release_year,
        source=s.source,
        watched=bool(s.watched),
        favorite=bool(s.favorite),
        last_played_at=s.last_played_at,

        data_origin=s.data_origin,
    )

def apply_patch_to_domain(item: MediaItem, p: MediaItemPatch) -> MediaItem:
    if p.kind is not None:
        item.kind = p.kind

    if p.size_bytes is not None: item.size_bytes = p.size_bytes
    if p.hash_sha256 is not None: item.hash_sha256 = p.hash_sha256
    if p.phash is not None: item.phash = p.phash

    if p.duration_sec is not None: item.duration_sec = p.duration_sec
    if p.width is not None: item.width = p.width
    if p.height is not None: item.height = p.height
    if p.fps is not None: item.fps = p.fps
    if p.bitrate is not None: item.bitrate = p.bitrate
    if p.codec_video is not None: item.codec_video = p.codec_video
    if p.codec_audio is not None: item.codec_audio = p.codec_audio
    if p.container is not None: item.container = p.container
    if p.aspect_ratio is not None: item.aspect_ratio = p.aspect_ratio
    if p.language is not None: item.language = p.language
    if p.has_subtitles is not None: item.has_subtitles = p.has_subtitles

    if p.title is not None: item.title = p.title
    if p.release_year is not None: item.release_year = p.release_year
    if p.source is not None: item.source = p.source
    if p.watched is not None: item.watched = p.watched
    if p.favorite is not None: item.favorite = p.favorite
    if p.last_played_at is not None: item.last_played_at = p.last_played_at

    if p.data_origin is not None: item.data_origin = p.data_origin
    return item

def to_read_schema(item: MediaItem) -> MediaItemRead:
    return MediaItemRead(
        id=item.id,  # Pydantic will handle UUID
        kind=item.kind,
        identity=MediaIdentityOut(
            media_folder=item.identity.media_folder,
            identity_name=item.identity.identity_name,
            video_ext=item.identity.video_ext,
        ),
        size_bytes=item.size_bytes,
        created_ts=item.created_ts,
        modified_ts=item.modified_ts,
        hash_sha256=item.hash_sha256,
        phash=item.phash,
        duration_sec=item.duration_sec,
        width=item.width, height=item.height, fps=item.fps,
        bitrate=item.bitrate,
        codec_video=item.codec_video, codec_audio=item.codec_audio,
        container=item.container, aspect_ratio=item.aspect_ratio,
        language=item.language, has_subtitles=bool(item.has_subtitles),
        title=item.title, release_year=item.release_year, source=item.source,
        watched=bool(item.watched), favorite=bool(item.favorite),
        last_played_at=item.last_played_at,
        date_created=item.date_created,
        last_updated=item.last_updated,
        data_origin=item.data_origin,
    )
