from __future__ import annotations
from pathlib import Path
from typing import Protocol
from hexmedia.domain.entities.probe import ProbeResult  # your domain result type

class MediaProbePort(Protocol):
    def probe(self, path: Path) -> ProbeResult: ...
