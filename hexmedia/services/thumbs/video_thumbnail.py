# hexmedia/services/thumbs/video_thumbnail.py
from __future__ import annotations
import os, re, shutil, subprocess, tempfile, json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple, List
from PIL import Image
from hexmedia.common.logging import get_logger

logger = get_logger()

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    s = hex_color.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        return (0, 0, 0)
    return (int(s[0:2],16), int(s[2:4],16), int(s[4:6],16))

def _safe_replace(tmp_path: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp_path, out_path)

@dataclass
class ProbeInfo:
    duration_sec: Optional[float]
    width: Optional[int]
    height: Optional[int]

class VideoThumbnail:
    def __init__(self, video_path: Path | str, ffmpeg: Optional[str] = None, ffprobe: Optional[str] = None):
        self.video = Path(video_path)
        self.ffmpeg = ffmpeg or os.getenv("XMEDIA_FFMPEG") or "ffmpeg"
        self.ffprobe = ffprobe or os.getenv("XMEDIA_FFPROBE") or "ffprobe"
        self._has_ffmpeg = (self.ffmpeg != "ffmpeg" and Path(self.ffmpeg).exists()) or shutil.which(self.ffmpeg) is not None
        self._has_ffprobe = (self.ffprobe != "ffprobe" and Path(self.ffprobe).exists()) or shutil.which(self.ffprobe) is not None

    def generate_thumbnail(
        self,
        out_path: Path | str,
        percent: float = 0.10,                # ~10% as requested
        format: str = "png",
        target_width: int = 960,
        allow_upscale: str = "if_smaller_than",
        quality: int = 95,
    ) -> Path:
        fmt = format.lower()
        out_path = Path(out_path)
        info = self._probe_basic()
        t = self._time_from_percent(percent, info.duration_sec)
        width_to_use = self._decide_width(info.width, target_width, allow_upscale)
        tmp = self._extract_frame_tmp(t, width_to_use)
        try:
            final = self._encode_to_format(tmp, out_path, fmt, quality)
        finally:
            tmp.unlink(missing_ok=True)
        return final

    def generate_collage(
        self,
        out_path: Path | str,
        percents: Sequence[float] = (10,20,30,40,50,60,70,80,90),
        grid: Tuple[int, int] = (3, 3),
        tile_width: int = 400,
        spacing: int = 6,
        bg: str = "#000000",
        format: str = "png",
        allow_upscale: str = "if_smaller_than",
        quality: int = 95,
    ) -> Optional[Path]:
        fmt = format.lower()
        out_path = Path(out_path)
        info = self._probe_basic()

        dur = info.duration_sec or 0
        if dur <= 0:
            logger.warning("No duration for %s; skipping collage", self.video)
            return None

        # normalize percents (accept 0..1 or 0..100)
        ps = []
        for p in percents:
            p = float(p)
            if p > 1.0: p = p / 100.0
            p = min(max(p, 0.01), 0.99)
            ps.append(round(p, 4))
        times = [dur * p for p in sorted(set(ps))]
        width_to_use = self._decide_width(info.width, tile_width, allow_upscale)

        tmp_paths: List[Path] = []
        try:
            for t in times:
                tmp_paths.append(self._extract_frame_tmp(t, width_to_use))

            rows, cols = grid
            if rows * cols < len(tmp_paths):
                tmp_paths = tmp_paths[: rows * cols]
            tiles = [Image.open(p).convert("RGB") for p in tmp_paths]
            cell_w = width_to_use
            cell_h = max(im.height for im in tiles) if tiles else int(cell_w * 9 / 16)
            bg_rgb = _hex_to_rgb(bg)

            sheet_w = cols * cell_w + (cols + 1) * spacing
            sheet_h = rows * cell_h + (rows + 1) * spacing
            from PIL import Image as PILImage
            sheet = PILImage.new("RGB", (sheet_w, sheet_h), color=bg_rgb)

            for i, im in enumerate(tiles):
                r = i // cols; c = i % cols
                x0 = spacing + c*(cell_w+spacing) + (cell_w - im.width)//2
                y0 = spacing + r*(cell_h+spacing) + (cell_h - im.height)//2
                sheet.paste(im, (x0, y0))

            with tempfile.NamedTemporaryFile("wb", suffix=f".{fmt}", delete=False, dir=str(out_path.parent)) as tf:
                tmp_out = Path(tf.name)
            try:
                self._pillow_save(sheet, tmp_out, fmt, quality)
                _safe_replace(tmp_out, out_path)
            finally:
                tmp_out.unlink(missing_ok=True)
        finally:
            for p in tmp_paths:
                p.unlink(missing_ok=True)
        return out_path

    # ---- internals ----
    def _probe_basic(self) -> ProbeInfo:
        if not self._has_ffprobe:
            return ProbeInfo(duration_sec=None, width=None, height=None)
        cmd = [self.ffprobe, "-v","error","-print_format","json","-show_format","-show_streams", str(self.video)]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            j = json.loads(out.decode("utf-8","replace"))
        except Exception:
            return ProbeInfo(duration_sec=None, width=None, height=None)
        dur = None; w = None; h = None
        try:
            fmt = j.get("format") or {}
            if "duration" in fmt: dur = float(fmt["duration"])
        except Exception: pass
        try:
            for s in j.get("streams", []):
                if s.get("codec_type") == "video":
                    w = s.get("width"); h = s.get("height"); break
        except Exception: pass
        return ProbeInfo(duration_sec=dur, width=w, height=h)

    def _decide_width(self, src_width: Optional[int], target_width: int, allow_upscale: str) -> int:
        allow_upscale = (allow_upscale or "if_smaller_than").lower()
        if src_width is None: return int(target_width)
        if src_width >= target_width: return int(target_width)
        if allow_upscale == "never": return int(src_width)
        return int(target_width)

    def _time_from_percent(self, percent: float, duration: Optional[float]) -> float:
        p = float(percent)
        if duration and duration > 0: return max(0.0, min(duration, duration * p))
        return max(0.0, 10.0 * p)  # fallback

    def _extract_frame_tmp(self, time_sec: float, width: int) -> Path:
        if not self._has_ffmpeg:
            raise RuntimeError("ffmpeg not found; install ffmpeg or set XMEDIA_FFMPEG")
        tmp_dir = self.video.parent if self.video.parent.exists() else Path(tempfile.gettempdir())
        with tempfile.NamedTemporaryFile("wb", suffix=".png", delete=False, dir=str(tmp_dir)) as tf:
            out_png = Path(tf.name)
        vf = f"scale={int(width)}:-1:flags=lanczos,setsar=1"
        cmd = [self.ffmpeg, "-hide_banner","-loglevel","error","-ss", f"{time_sec:.3f}", "-i", str(self.video),
               "-frames:v","1","-an","-vf", vf,"-y", str(out_png)]
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            out_png.unlink(missing_ok=True)
            raise RuntimeError(f"ffmpeg failed extracting frame at {time_sec:.3f}s: {e}") from e
        return out_png

    def _encode_to_format(self, tmp_png: Path, out_path: Path, fmt: str, quality: int) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "png":
            _safe_replace(tmp_png, out_path); return out_path
        img = Image.open(tmp_png)
        if fmt in ("jpg","jpeg"):
            img = img.convert("RGB")
            with tempfile.NamedTemporaryFile("wb", suffix=".jpg", delete=False, dir=str(out_path.parent)) as tf:
                tmp_out = Path(tf.name)
            try:
                img.save(tmp_out, format="JPEG", quality=int(quality), subsampling=0, optimize=True, progressive=True)
                _safe_replace(tmp_out, out_path)
            finally:
                tmp_out.unlink(missing_ok=True)
            return out_path
        if fmt == "webp":
            with tempfile.NamedTemporaryFile("wb", suffix=".webp", delete=False, dir=str(out_path.parent)) as tf:
                tmp_out = Path(tf.name)
            try:
                img.save(tmp_out, format="WEBP", quality=int(quality), method=6)
                _safe_replace(tmp_out, out_path)
            finally:
                tmp_out.unlink(missing_ok=True)
            return out_path
        raise ValueError(f"Unsupported format: {fmt}")

    def _pillow_save(self, img: Image.Image, path: Path, fmt: str, quality: int) -> None:
        fmt = fmt.lower()
        if fmt == "png":
            img.save(path, format="PNG", optimize=True)
        elif fmt in ("jpg","jpeg"):
            img = img.convert("RGB")
            img.save(path, format="JPEG", quality=int(quality), subsampling=0, optimize=True, progressive=True)
        elif fmt == "webp":
            img.save(path, format="WEBP", quality=int(quality), method=6)
        else:
            raise ValueError(f"Unsupported format: {fmt}")
