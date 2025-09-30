from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ProbeResult:
    # DB-facing fields
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

    # Optional raw payload for debugging
    raw: Dict[str, Any] = field(default_factory=dict)
