from __future__ import annotations

import hashlib
from pathlib import Path

from hexmedia.domain.ports.hashing import HashingPort


class SimpleHashing(HashingPort):
    """
    Streaming SHA-256 file hasher. Memory efficient for large files.
    """

    def sha256_file(self, path: Path, chunk_size: int = 1024 * 1024) -> str:
        if not isinstance(path, Path):
            path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"File to hash not found: {path}")

        h = hashlib.sha256()
        # Buffered read in fixed chunks
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()
