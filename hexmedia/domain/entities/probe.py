# hexmedia/domain/entities/probe.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProbeResult:
    """
    Normalized, framework-free result of a media probe (e.g., ffprobe).
    Intended to be produced by an adapter and then merged into a MediaItem.
    Only technical attributes here—no identity or curation.
    """
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
    size_bytes: Optional[int] = None
