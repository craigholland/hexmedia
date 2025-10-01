from __future__ import annotations
from pathlib import Path
from typing import Protocol
from hexmedia.domain.entities.probe import ProbeResult

class MediaProbePort(Protocol):
    # def __init__(self, input_path: str, *, extra_args: list[str] | None = None): ...
    def probe(self, path: Path) -> ProbeResult: ...
