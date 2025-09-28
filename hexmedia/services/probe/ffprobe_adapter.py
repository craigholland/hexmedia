# hexmedia/services/probe/ffprobe_adapter.py
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from hexmedia.common.settings import get_settings
from hexmedia.common.logging import get_logger
from hexmedia.domain.entities.probe import ProbeResult
from hexmedia.domain.ports.probe import MediaProbePort

logger = get_logger()


@dataclass(frozen=True)
class FFprobeError(RuntimeError):
    """Adapter-level error for probe failures."""
    message: str
    stderr: Optional[str] = None
    rc: Optional[int] = None


class FFprobeAdapter(MediaProbePort):
    """
    Infrastructure adapter implementing MediaProbePort using `ffprobe`.
    Safe for use from ThreadManager (I/O-bound).
    """

    def __init__(self, ffprobe_bin: Optional[str] = None, timeout_sec: Optional[int] = None):
        cfg = get_settings()
        # choose binary
        candidate = ffprobe_bin or cfg.FFPROBE_BIN
        if not candidate or candidate == "ffprobe":
            # try to resolve absolute path for nicer errors
            resolved = shutil.which(candidate or "ffprobe")
            if not resolved:
                raise FFprobeError("ffprobe not found on PATH; set FFPROBE_BIN or install ffmpeg.")
            candidate = resolved

        self.ffprobe_bin = candidate
        self.timeout_sec = int(timeout_sec or cfg.PROBE_TIMEOUT_SEC or 15)

    # ---- Port API -------------------------------------------------------------
    def probe(self, path: Path) -> ProbeResult:
        if not path:
            raise FFprobeError("No path provided to probe().")
        if not Path(path).is_file():
            raise FFprobeError(f"File not found: {path}")

        cmd = [
            self.ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                check=False,  # we handle rc manually to attach stderr
            )
        except subprocess.TimeoutExpired as e:
            raise FFprobeError(f"ffprobe timed out after {self.timeout_sec}s", stderr=str(e)) from e
        except OSError as e:
            raise FFprobeError("Failed to execute ffprobe (OS error).", stderr=str(e)) from e

        if proc.returncode != 0:
            raise FFprobeError("ffprobe returned non-zero exit code", stderr=proc.stderr, rc=proc.returncode)

        try:
            data = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError as e:
            raise FFprobeError("ffprobe produced invalid JSON", stderr=proc.stdout) from e

        return self._parse_ffprobe_json(data)

    # ---- Parsing helpers ------------------------------------------------------
    @staticmethod
    def _parse_ffprobe_json(data: dict) -> ProbeResult:
        fmt = data.get("format") or {}
        streams = list(data.get("streams") or [])

        # choose video stream: default disposition first, else highest resolution
        def _is_default_video(s: dict) -> bool:
            return s.get("codec_type") == "video" and (s.get("disposition", {}) or {}).get("default") == 1

        def _res_key(s: dict) -> int:
            try:
                return int(s.get("width", 0)) * int(s.get("height", 0))
            except Exception:
                return 0

        vstreams = [s for s in streams if s.get("codec_type") == "video"]
        astreams = [s for s in streams if s.get("codec_type") == "audio"]
        sstreams = [s for s in streams if s.get("codec_type") == "subtitle"]

        vstream = next((s for s in vstreams if _is_default_video(s)), None)
        if vstream is None and vstreams:
            vstream = max(vstreams, key=_res_key)

        astream = astreams[0] if astreams else None

        # duration (prefer format.duration)
        duration_sec = _parse_float(fmt.get("duration"))
        if duration_sec is not None:
            duration_sec = int(duration_sec)
        else:
            # fallback: max stream duration
            dur_candidates = [_parse_float(s.get("duration")) for s in streams]
            dur_candidates = [d for d in dur_candidates if d is not None]
            duration_sec = int(max(dur_candidates)) if dur_candidates else None

        # fps from avg_frame_rate or r_frame_rate
        fps = None
        if vstream:
            fps = _parse_rate(vstream.get("avg_frame_rate")) or _parse_rate(vstream.get("r_frame_rate"))

        # bitrate: format-level or sum of stream bitrates
        bitrate = _parse_int(fmt.get("bit_rate"))
        if bitrate is None:
            sb = [_parse_int(s.get("bit_rate")) for s in streams]
            sb = [x for x in sb if x is not None]
            bitrate = sum(sb) if sb else None

        # language (best-effort): prefer video->tags->language, else format tags, else audio
        language = (
            _get_tag(vstream, "language")
            or _get_tag(fmt, "language")
            or _get_tag(astream, "language")
        )

        has_subs = bool(sstreams)

        return ProbeResult(
            duration_sec=duration_sec,
            width=_parse_int(vstream.get("width")) if vstream else None,
            height=_parse_int(vstream.get("height")) if vstream else None,
            fps=fps,
            bitrate=bitrate,
            codec_video=(vstream or {}).get("codec_name") if vstream else None,
            codec_audio=(astream or {}).get("codec_name") if astream else None,
            container=fmt.get("format_name"),
            aspect_ratio=(vstream or {}).get("display_aspect_ratio") if vstream else None,
            language=language,
            has_subtitles=has_subs,
            size_bytes=_parse_int(fmt.get("size")),
        )


# ---- tiny parse helpers -------------------------------------------------------
def _parse_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

def _parse_int(x) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(float(x))
    except Exception:
        return None

def _parse_rate(rate: Optional[str]) -> Optional[float]:
    if not rate or "/" not in rate:
        return None
    try:
        n, d = rate.split("/", 1)
        n, d = float(n), float(d)
        if d == 0:
            return None
        return n / d
    except Exception:
        return None

def _get_tag(obj: dict | None, key: str) -> Optional[str]:
    if not obj:
        return None
    tags = obj.get("tags") or {}
    if not isinstance(tags, dict):
        return None
    val = tags.get(key)
    return str(val) if val is not None else None
