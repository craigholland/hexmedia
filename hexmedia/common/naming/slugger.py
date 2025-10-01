# hexmedia/common/naming/slugger.py
from __future__ import annotations

import secrets
import string
from typing import Iterable
import re
import unicodedata

DEFAULT_ALPHABET = string.ascii_lowercase  # 'a'..'z'


def random_slug(length: int = 7, alphabet: Iterable[str] = DEFAULT_ALPHABET) -> str:
    """Generate a short, filesystem-friendly slug (default: 7 lowercase letters)."""
    pool = tuple(alphabet)
    return "".join(secrets.choice(pool) for _ in range(length))

_slug_re = re.compile(r"[^a-z0-9]+")
_slug_re_unicode = re.compile(r"\s+")

def slugify(text: str, *, max_len: int = 64, allow_unicode: bool = False) -> str:
    """
    Deterministic, human-readable slug:
      - lowercases
      - NFKD normalize; optionally strip to ASCII if allow_unicode=False
      - collapse separators to single '-'
      - trim leading/trailing '-'
      - truncate to `max_len`
      - returns '' if nothing remains (caller may fallback to random_slug())

    Examples:
      "Exterior Color" -> "exterior-color"
      "  Funny__Name!! " -> "funny-name"
      "Éxämple" (ascii) -> "example"
      "车辆颜色" (ascii) -> ""  (use random_slug fallback)
      "车辆颜色" (allow_unicode=True) -> "车辆颜色"
    """
    if text is None:
        return ""

    value = str(text).strip().lower()

    if allow_unicode:
        # Normalize but keep unicode letters; collapse any whitespace to single dashes
        value = unicodedata.normalize("NFKC", value)
        value = _slug_re_unicode.sub("-", value)
        value = value.strip("-")
    else:
        # Normalize to ASCII
        value = unicodedata.normalize("NFKD", value)
        value = value.encode("ascii", "ignore").decode("ascii")
        value = _slug_re.sub("-", value).strip("-")

    if max_len > 0 and len(value) > max_len:
        value = value[:max_len].rstrip("-")

    return value

def slugify_path(parts: Iterable[str], *, allow_unicode: bool = False, max_part_len: int = 64) -> str:
    """
    Slugify a sequence of path parts and join with '/'.
    Empty parts are discarded; parts that slugify to '' are also dropped.
    """
    slugs = []
    for p in parts:
        s = slugify(p, max_len=max_part_len, allow_unicode=allow_unicode)
        if s:
            slugs.append(s)
    return "/".join(slugs)
