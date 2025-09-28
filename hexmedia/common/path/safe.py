# xvideo/common/path/safe.py
from __future__ import annotations

import os
from pathlib import Path


def resolve_root(root: Path | str) -> Path:
    """Resolve a project/media root directory."""
    return Path(root).expanduser().resolve()


def safe_join(root: Path | str, rel: Path | str) -> Path:
    """
    Join 'root' and a relative path safely, ensuring the result stays inside 'root'.
    Raises ValueError if traversal escapes the root.
    """
    r = resolve_root(root)
    p = (r / str(rel)).resolve()
    try:
        p.relative_to(r)  # type: ignore[attr-defined]
    except Exception as exc:
        # Fallback for older Python if needed
        if not str(p).startswith(str(r) + os.sep):
            raise ValueError(f"path {p} escapes root {r}") from exc
    return p


def ensure_inside(path: Path | str, root: Path | str) -> None:
    """Validate that 'path' is inside 'root'. Raises ValueError if not."""
    p = Path(path).resolve()
    r = resolve_root(root)
    try:
        p.relative_to(r)  # type: ignore[attr-defined]
    except Exception:
        if not str(p).startswith(str(r) + os.sep):
            raise ValueError(f"path {p} escapes root {r}")
