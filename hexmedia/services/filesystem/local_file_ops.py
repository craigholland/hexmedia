from __future__ import annotations

import os
import shutil
from pathlib import Path

from hexmedia.domain.ports.files import FileOpsPort


class LocalFileOps(FileOpsPort):
    """
    Local filesystem implementation for FileOpsPort.
    """

    def ensure_dir(self, path: Path) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)

    def move_file(self, src: Path, dst: Path, *, overwrite: bool = False) -> None:
        src_p = Path(src)
        dst_p = Path(dst)

        if not src_p.is_file():
            raise FileNotFoundError(f"Source file not found: {src_p}")

        dst_p.parent.mkdir(parents=True, exist_ok=True)

        if dst_p.exists():
            if not overwrite:
                raise FileExistsError(f"Destination exists: {dst_p}")
            # Try atomic replace when possible (same filesystem)
            try:
                os.replace(src_p, dst_p)
                return
            except OSError:
                # Fall back to remove-then-move (cross-device etc.)
                try:
                    dst_p.unlink()
                except FileNotFoundError:
                    pass

        # shutil.move handles cross-device moves (copy+unlink)
        shutil.move(str(src_p), str(dst_p))

    def file_exists(self, path: Path) -> bool:
        return Path(path).exists()
