# xvideo/common/naming/slugger.py
from __future__ import annotations

import secrets
import string
from typing import Iterable


DEFAULT_ALPHABET = string.ascii_lowercase  # 'a'..'z'


def random_slug(length: int = 7, alphabet: Iterable[str] = DEFAULT_ALPHABET) -> str:
    """Generate a short, filesystem-friendly slug (default: 7 lowercase letters)."""
    pool = tuple(alphabet)
    return "".join(secrets.choice(pool) for _ in range(length))
