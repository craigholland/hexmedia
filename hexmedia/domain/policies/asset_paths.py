from __future__ import annotations

from typing import Dict

def asset_relative_paths(thumb_fmt: str, sheet_fmt: str) -> Dict[str, str]:
    """
    Domain policy for where assets live *relative to the item's directory*.
    """
    return {
        "thumb": f"assets/thumb.{thumb_fmt}",
        "contact_sheet": f"assets/contact_sheet.{sheet_fmt}",
    }

def preferred_collage_grid(num_tiles: int = 9) -> tuple[int, int]:
    """
    For now we always do 3x3 if num_tiles==9; keep logic centralized if we add variants later.
    """
    if num_tiles == 9:
        return (3, 3)
    # Simple fallback heuristic: square-ish
    from math import sqrt, floor, ceil
    rows = floor(sqrt(num_tiles))
    cols = ceil(num_tiles / rows)
    return rows, cols
