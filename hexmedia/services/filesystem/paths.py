import shutil
from pathlib import Path
from hexmedia.common.settings import get_settings

def build_item_dir(bucket: str, identity: str) -> Path:
    return get_settings().media_root / bucket / identity

def build_item_file_path(bucket: str, identity: str, ext: str) -> Path:
    name = f"{identity}.{ext}" if ext else identity
    return build_item_dir(bucket, identity) / name


def ensure_item_dir(media_root: Path, bucket: str, identity: str) -> Path:
    """
    Ensure /<media_root>/<bucket>/<identity>/ exists and return that path.
    """
    item_dir = Path(media_root) / bucket / identity
    item_dir.mkdir(parents=True, exist_ok=True)
    return item_dir


def move_into_item_dir(src: Path, item_dir: Path, identity: str, ext: str) -> Path:
    """
    Move the file at `src` into `item_dir` with the canonical filename `<identity>.<ext>`.
    Returns the destination path.
    """
    ext = (ext or "").lstrip(".")
    dest_name = f"{identity}.{ext}" if ext else identity
    dest_path = item_dir / dest_name
    # Use replace to be idempotent if something already exists (e.g., re-runs)
    if dest_path.exists():
        dest_path.unlink()
    shutil.move(str(src), str(dest_path))
    return dest_path
