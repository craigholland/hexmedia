# tests/domain/test_ingest_planner.py
from __future__ import annotations

from pathlib import Path
import os

import pytest

from hexmedia.domain.policies.ingest_planner import IngestPlanner
from hexmedia.domain.dataclasses.ingest import IngestPlanItem


def _touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"dummy")
    return p


class FakeRepoCounts:
    """Repo that provides explicit bucket counts via count_media_items_by_bucket()."""
    def __init__(self, counts):
        self._counts = counts

    def count_media_items_by_bucket(self):
        # may return keys like "00", "2", "a9", "xyz" etc.  Planner must normalize to base36 3-char.
        return dict(self._counts)


class FakeRepoIter:
    """Repo that only iterates existing media_folder values."""
    def __init__(self, media_folders):
        # e.g. ["00/abc", "002/xyz", "0a9/pqr"]
        self._mfs = list(media_folders)

    def iter_media_folders(self):
        for mf in self._mfs:
            yield mf


_BASE36 = set("0123456789abcdefghijklmnopqrstuvwxyz")


def _is_base36_3(s: str) -> bool:
    return len(s) == 3 and all(ch in _BASE36 for ch in s)


# -------------------------
# classification & shaping
# -------------------------

def test_plan_classifies_and_marks_supported(tmp_path, monkeypatch):
    # keep environment deterministic
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "3")

    files = [
        _touch(tmp_path / "clip.mp4"),
        _touch(tmp_path / "photo.jpg"),
        _touch(tmp_path / "notes.txt"),
        _touch(tmp_path / "noext"),
    ]

    planner = IngestPlanner(query_repo=None)
    # tighten to 3 buckets so test is small / deterministic
    planner._bucket_max = 3  # type: ignore[attr-defined]

    plan = planner.plan(files)

    # All items are IngestPlanItem
    assert all(isinstance(pi, IngestPlanItem) for pi in plan)

    # mp4 should be video & supported
    mp4 = next(pi for pi in plan if pi.src.name == "clip.mp4")
    assert mp4.kind == "video"
    assert mp4.supported is True
    assert mp4.ext == "mp4"

    # jpg should be image & supported
    jpg = next(pi for pi in plan if pi.src.name == "photo.jpg")
    assert jpg.kind == "image"
    assert jpg.supported is True
    assert jpg.ext == "jpg"

    # unknown extension should be marked unsupported
    txt = next(pi for pi in plan if pi.src.name == "notes.txt")
    assert txt.kind == "unknown"  # not in video/image sets
    assert txt.supported is False

    # file with no extension -> ext == "" and unknown
    noext = next(pi for pi in plan if pi.src.name == "noext")
    assert noext.ext == ""
    assert noext.kind == "unknown"
    assert noext.supported is False

    # verify basic shape: media_folder, dest_filename, identity_name
    for pi in plan:
        # bucket must be 3-char base36
        assert _is_base36_3(pi.bucket)
        assert "/" in pi.media_folder  # "<bucket>/<item>"
        assert pi.dest_rel_dir == pi.media_folder
        assert pi.identity_name and len(pi.identity_name) == 12
        # dest filename either "<identity>.<ext>" or just identity if no ext
        if pi.ext:
            assert pi.dest_filename == f"{pi.identity_name}.{pi.ext}"
        else:
            assert pi.dest_filename == pi.identity_name


# -------------------------
# bucket selection behavior
# -------------------------

def test_bucket_balancing_prefers_smallest_from_repo_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "10")
    # Seed counts so that '002' (formerly '02') is clearly the smallest
    repo = FakeRepoCounts({"00": 7, "01": 3, "02": 0, "03": 8})

    files = [
        _touch(tmp_path / "a.mp4"),
        _touch(tmp_path / "b.mp4"),
    ]

    planner = IngestPlanner(query_repo=repo)
    plan = planner.plan(files)

    # first file should go to the truly smallest bucket -> '002'
    assert plan[0].bucket == "002"
    # after incrementing once, it's still smallest vs 3 and 7 -> stays '002'
    assert plan[1].bucket == "002"


def test_bucket_counts_fallback_initializes_zero_to_bucket_max(monkeypatch, tmp_path):
    # No repo → we initialize buckets 000..N-1 (base36) with zeros
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "4")

    f = _touch(tmp_path / "x.mp4")
    planner = IngestPlanner(query_repo=None)
    planner._bucket_max = 4  # ensure we use a tiny set for the test

    counts = planner.get_bucket_counts()
    assert set(counts.keys()) == {"000", "001", "002", "003"}
    # planning a single file should pick the lexicographically first min ("000")
    pi = planner.plan([f])[0]
    assert pi.bucket == "000"


def test_bucket_counts_can_derive_from_iterating_media_folders(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "5")

    repo = FakeRepoIter([
        "00/abc", "00/def",
        "02/qqq",
        "04/mmm", "04/nnn", "04/ppp",
    ])
    planner = IngestPlanner(query_repo=repo)
    f = _touch(tmp_path / "z.mp4")

    # counts derived (normalized): 000->2, 002->1, 004->3 -> min is "002"
    pi = planner.plan([f])[0]
    assert pi.bucket == "002"


def test_alpha_buckets_when_overflowing_digits(monkeypatch, tmp_path):
    """
    Ensure planner handles alpha base36 keys (e.g., '00a') and can select them.
    """
    # Need at least 12 buckets to reach '00a'
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "12")

    # Pre-seed counts such that '00a' is the unique minimum
    repo = FakeRepoCounts({
        "000": 5, "001": 5, "002": 5, "003": 5, "004": 5,
        "005": 5, "006": 5, "007": 5, "008": 5, "009": 5,
        "00a": 0, "00b": 7,
    })

    f = _touch(tmp_path / "alpha.mkv")
    planner = IngestPlanner(query_repo=repo)
    pi = planner.plan([f])[0]
    assert pi.bucket == "00a"
    assert _is_base36_3(pi.bucket)


def test_normalizes_incoming_bucket_keys_from_repo(monkeypatch, tmp_path):
    """
    Repo may return weird keys ('2', '01', 'a9'); planner must normalize to
    3-char base36 ('002', '001', '0a9').
    """
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "100")

    repo = FakeRepoCounts({
        "2": 0,      # decimal 2 -> '2' base36 -> '002'
        "01": 3,     # '01' -> '001'
        "a9": 0,     # base36 'a9' -> '0a9'
    })
    planner = IngestPlanner(query_repo=repo)

    counts = planner.get_bucket_counts()
    # Ensure normalized keys are present
    assert "002" in counts
    assert "001" in counts
    assert "0a9" in counts

    # With equal minimum (002 and 0a9 both 0), planner chooses lexicographically
    f = _touch(tmp_path / "pick.mp4")
    pi = planner.plan([f])[0]
    assert pi.bucket in ("002", "0a9")
    assert pi.bucket == min("002", "0a9")  # tie-break lexicographically
    assert _is_base36_3(pi.bucket)


# -------------------------
# shape invariants
# -------------------------

def test_media_folder_and_names_are_consistent(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "2")
    f = _touch(tmp_path / "movie.mov")

    planner = IngestPlanner(query_repo=None)
    planner._bucket_max = 2  # type: ignore[attr-defined]

    [pi] = planner.plan([f])

    # bucket is 3-char base36
    assert _is_base36_3(pi.bucket)

    # media_folder = "<bucket>/<item>"
    assert pi.media_folder == f"{pi.bucket}/{pi.item}"

    # identity_name used in dest_filename
    assert pi.dest_filename.startswith(pi.identity_name)
    assert pi.dest_filename.endswith(".mov")
