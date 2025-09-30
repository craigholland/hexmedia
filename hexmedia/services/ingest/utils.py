from __future__ import annotations

from pathlib import Path
from hexmedia.common.settings import get_settings
import hashlib

def is_supported_media_file(p: Path) -> bool:
    """Accept only whitelisted video/image extensions."""
    if not p.is_file():
        return False
    if p.name.startswith("."):
        return False
    ext = p.suffix.lower().lstrip(".")
    cfg = get_settings()
    return ext in set(cfg.video_exts) | set(cfg.image_exts)


def sha256_of_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()