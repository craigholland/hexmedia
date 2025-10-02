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
        # e.g. {"00": 3, "01": 0, "02": 7}
        return dict(self._counts)


class FakeRepoIter:
    """Repo that only iterates existing media_folder values."""
    def __init__(self, media_folders):
        # e.g. ["00/abc", "02/xyz", "02/pqr"]
        self._mfs = list(media_folders)

    def iter_media_folders(self):
        for mf in self._mfs:
            yield mf


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
    assert txt.kind == "unknown"  # not in video/image/sidecar sets
    assert txt.supported is False

    # file with no extension -> ext == "" and unknown
    noext = next(pi for pi in plan if pi.src.name == "noext")
    assert noext.ext == ""
    assert noext.kind == "unknown"
    assert noext.supported is False

    # verify basic shape: media_folder, dest_filename, identity_name
    for pi in plan:
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
    # Seed counts so that '02' is clearly the smallest
    repo = FakeRepoCounts({"00": 7, "01": 3, "02": 0, "03": 8})

    files = [
        _touch(tmp_path / "a.mp4"),
        _touch(tmp_path / "b.mp4"),
    ]

    planner = IngestPlanner(query_repo=repo)
    plan = planner.plan(files)

    # first file should go to the truly smallest bucket -> '02'
    assert plan[0].bucket == "02"
    # after incrementing once, it's still smallest (1 vs 3 and 7) -> stays '02'
    assert plan[1].bucket == "02"


def test_bucket_counts_fallback_initializes_zero_to_bucket_max(monkeypatch, tmp_path):
    # No repo → we initialize buckets 00..N-1 with zeros
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "4")

    f = _touch(tmp_path / "x.mp4")
    planner = IngestPlanner(query_repo=None)
    planner._bucket_max = 4  # ensure we use a tiny set for the test

    counts = planner.get_bucket_counts()
    assert set(counts.keys()) == {"00", "01", "02", "03"}
    # planning a single file should pick the lexicographically first min ("00")
    pi = planner.plan([f])[0]
    assert pi.bucket == "00"


def test_bucket_counts_can_derive_from_iterating_media_folders(monkeypatch, tmp_path):
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "5")

    repo = FakeRepoIter([
        "00/abc", "00/def",
        "02/qqq",
        "04/mmm", "04/nnn", "04/ppp",
    ])
    planner = IngestPlanner(query_repo=repo)
    f = _touch(tmp_path / "z.mp4")

    # counts derived: 00->2, 02->1, 04->3 -> min is "02"
    pi = planner.plan([f])[0]
    assert pi.bucket == "02"


# -------------------------
# shape invariants
# -------------------------

def test_media_folder_and_names_are_consistent(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXMEDIA_BUCKET_MAX", "2")
    f = _touch(tmp_path / "movie.mov")

    planner = IngestPlanner(query_repo=None)
    planner._bucket_max = 2  # type: ignore[attr-defined]

    [pi] = planner.plan([f])

    # media_folder = "<bucket>/<item>"
    assert pi.media_folder == f"{pi.bucket}/{pi.item}"

    # identity_name used in dest_filename
    assert pi.dest_filename.startswith(pi.identity_name)
    assert pi.dest_filename.endswith(".mov")
