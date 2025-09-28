from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence, Tuple
from hexmedia.domain.enums.upscale_policy import UpscalePolicy


class ThumbnailsPort(Protocol):
    def generate_thumbnail(
        self,
        video_path: Path,
        out_path: Path,
        at_percent: float,          # e.g. 0.2 = 20% into the video
        target_width: int,
        format: str,                # "png" | "jpg" | "webp"
        allow_upscale: UpscalePolicy,
    ) -> Path: ...

    def generate_collage(
        self,
        video_path: Path,
        out_path: Path,
        percents: Sequence[float],  # e.g. [0.1, 0.2, ..., 0.9]
        tile_width: int,
        grid: Tuple[int, int],      # rows, cols
        format: str,
        allow_upscale: UpscalePolicy,
    ) -> Path: ...
