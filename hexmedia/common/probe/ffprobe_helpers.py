# hexmedia/common/probe/ffprobe_helpers.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import json
import shlex
import subprocess

from hexmedia.common.logging import get_logger
logger = get_logger()

def build_ffprobe_cmd(input_path: str | Path, extra_args: Iterable[str] | None = None) -> List[str]:
    """
    Build a robust ffprobe command that emits JSON we can parse consistently.
    """
    if isinstance(input_path, Path):
        input_path = str(input_path)
    base = [
        "ffprobe",
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-print_format", "json",
        "--",  # Stop option parsing in case of weird filenames
        input_path,
    ]
    if extra_args:
        # Insert before the path (after -- we avoid interfering with options)
        base = base[:-1] + list(extra_args) + base[-1:]
    return base

def run_ffprobe(cmd: List[str]) -> Dict[str, Any]:
    """
    Execute ffprobe and return parsed JSON. Raises CalledProcessError on failure.
    """
    logger.debug("ffprobe cmd: %s", " ".join(shlex.quote(p) for p in cmd))
    cp = subprocess.run(cmd, capture_output=True, text=True, check=True)
    try:
        data = json.loads(cp.stdout or "{}")
    except json.JSONDecodeError as e:
        logger.exception("Failed to parse ffprobe JSON")
        raise RuntimeError("ffprobe produced invalid JSON") from e
    return data

def parse_ffprobe(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the fields we care about (duration, dimensions, fps, codecs, etc.)
    from ffprobe JSON. Safe to call in unit tests with fixture JSON.
    """
    fmt = (data or {}).get("format", {}) or {}
    streams = (data or {}).get("streams", []) or []

    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    s_streams = [s for s in streams if s.get("codec_type") == "subtitle"]

    def _maybe_int(x):
        try: return int(float(x))
        except Exception: return None

    def _maybe_float(x):
        try: return float(x)
        except Exception: return None

    # fps commonly appears as "num/den" in r_frame_rate
    def _fps_from_fraction(fr: str | None) -> float | None:
        if not fr or "/" not in fr:
            return _maybe_float(fr)
        num, den = fr.split("/", 1)
        try:
            n = float(num); d = float(den) or 1.0
            return n / d
        except Exception:
            return None

    parsed: Dict[str, Any] = {
        "duration_sec": _maybe_int(fmt.get("duration")),
        "container": fmt.get("format_name"),
        "bitrate": _maybe_int(fmt.get("bit_rate")),
        "language": (v_stream or {}).get("tags", {}).get("language") or fmt.get("tags", {}).get("language"),
        "has_subtitles": bool(s_streams),
        "codec_video": (v_stream or {}).get("codec_name"),
        "codec_audio": (a_stream or {}).get("codec_name"),
        "width": _maybe_int((v_stream or {}).get("width")),
        "height": _maybe_int((v_stream or {}).get("height")),
        "fps": _fps_from_fraction((v_stream or {}).get("r_frame_rate")),
        "aspect_ratio": (v_stream or {}).get("display_aspect_ratio") or (v_stream or {}).get("sample_aspect_ratio"),
    }
    return parsed
