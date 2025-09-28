from __future__ import annotations
from pathlib import Path
from typing import Protocol

class HashingPort(Protocol):
    def sha256_file(self, path: Path) -> str: ...
