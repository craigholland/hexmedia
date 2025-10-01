# hexmedia/database/repos/_mapping.py
from __future__ import annotations
from hexmedia.database.models.media import MediaItem as DBMediaItem
from hexmedia.domain.entities.media_item import MediaItem as DomainMediaItem
from hexmedia.domain.enums.media_kind import MediaKind

def to_domain_media_item(row: DBMediaItem) -> DomainMediaItem:
    # Minimal, same as your _to_domain (removed logging noise)
    return DomainMediaItem(
        id=row.id,
        kind=row.kind.value if isinstance(row.kind, MediaKind) else str(row.kind),
        media_folder=row.media_folder,
        identity_name=row.identity_name,
        video_ext=row.video_ext,
        size_bytes=row.size_bytes,
        hash_sha256=row.hash_sha256,
        duration_sec=row.duration_sec,
        width=row.width,
        height=row.height,
        fps=float(row.fps) if row.fps is not None else None,
        bitrate=row.bitrate,
        codec_video=row.codec_video,
        codec_audio=row.codec_audio,
        container=row.container,
        aspect_ratio=row.aspect_ratio,
        language=row.language,
        has_subtitles=row.has_subtitles,
        title=row.title,
        release_year=row.release_year,
        source=row.source,
        watched=row.watched,
        favorite=row.favorite,
        last_played_at=row.last_played_at,
        # date_created/last_updated/data_origin if present on your ORM base
        date_created=getattr(row, "date_created", None),
        last_updated=getattr(row, "last_updated", None),
        data_origin=getattr(row, "data_origin", None),
    )
