# tests/services/test_thumb_service_invocation.py
from __future__ import annotations
import uuid
import pytest
from sqlalchemy.orm import sessionmaker


import hexmedia.services.ingest.thumb_service as svc_mod
from hexmedia.services.ingest.thumb_service import ThumbService
from hexmedia.database.repos.media_query import MediaQueryRepo


class _FakeThumbWorker:
    """Test double that records ctor kwargs and per-item calls."""
    instances = []
    ctor_args = []
    process_calls = []

    def __init__(self, *args, **kwargs):
        _FakeThumbWorker.instances.append(self)
        _FakeThumbWorker.ctor_args.append(kwargs)

    def process_one(self, media_item_id: str, rel_dir: str, file_name: str):
        _FakeThumbWorker.process_calls.append((media_item_id, rel_dir, file_name))
        # mimic a successful generation result (what the service aggregates)
        return {"generated": 1, "updated": 1, "skipped": 0, "errors": 0}


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeThumbWorker.instances.clear()
    _FakeThumbWorker.ctor_args.clear()
    _FakeThumbWorker.process_calls.clear()
    yield
    _FakeThumbWorker.instances.clear()
    _FakeThumbWorker.ctor_args.clear()
    _FakeThumbWorker.process_calls.clear()


def test_thumb_service_calls_repo_and_worker_with_flags_and_limit(monkeypatch, db_engine):
    """
    - Service queries candidates with (limit, regenerate).
    - Constructs ThumbWorker with passed flags.
    - Calls process_one for each candidate and aggregates report fields.
    """
    monkeypatch.setattr(svc_mod, "ThumbWorker", _FakeThumbWorker, raising=True)

    called = {"limit": None, "regenerate": None}

    def _fake_find_video_candidates_for_thumbs(self, *, limit: int, regenerate: bool):
        called["limit"] = limit
        called["regenerate"] = regenerate
        return [
            (str(uuid.uuid4()), "00/abc", "abc.mp4"),
            (str(uuid.uuid4()), "01/def", "def.mp4"),
        ]

    monkeypatch.setattr(
        MediaQueryRepo,
        "find_video_candidates_for_thumbs",
        _fake_find_video_candidates_for_thumbs,
        raising=True,
    )

    SessionLocal = sessionmaker(bind=db_engine, future=True)
    with SessionLocal() as db:
        service = ThumbService(db)
        rep = service.run(
            limit=7,
            regenerate=False,
            workers=1,
            include_missing=False,
            thumb_format="png",
            collage_format="png",
            thumb_width=640,
            tile_width=320,
            upscale_policy="if_smaller_than",
        )

    # repo called with expected args
    assert called["limit"] == 7
    assert called["regenerate"] is False

    # worker constructed with expected options
    assert len(_FakeThumbWorker.instances) == 1
    ctor = _FakeThumbWorker.ctor_args[0]
    assert ctor.get("regenerate") is False
    assert ctor.get("include_missing") is False
    assert ctor.get("thumb_format") == "png"
    assert ctor.get("collage_format") == "png"
    assert ctor.get("thumb_width") == 640
    assert ctor.get("tile_width") == 320
    assert ctor.get("upscale_policy") == "if_smaller_than"

    # one process call per candidate
    assert len(_FakeThumbWorker.process_calls) == 2

    # duck-typed checks on the report
    assert getattr(rep, "scanned", None) == 2
    assert getattr(rep, "generated", None) == 2
    assert getattr(rep, "updated", None) == 2
    assert getattr(rep, "skipped", None) == 0
    assert getattr(rep, "errors", None) == 0
    # started_at / finished_at present
    assert getattr(rep, "started_at", None) is not None
    assert getattr(rep, "finished_at", None) is not None


def test_thumb_service_no_candidates_skips_worker(monkeypatch, db_engine):
    """No candidates -> no worker instances and an empty run report."""
    monkeypatch.setattr(svc_mod, "ThumbWorker", _FakeThumbWorker, raising=True)

    def _fake_empty(self, *, limit: int, regenerate: bool):
        return []

    monkeypatch.setattr(
        MediaQueryRepo,
        "find_video_candidates_for_thumbs",
        _fake_empty,
        raising=True,
    )

    SessionLocal = sessionmaker(bind=db_engine, future=True)
    with SessionLocal() as db:
        service = ThumbService(db)
        rep = service.run(
            limit=5,
            regenerate=False,
            workers=1,
            include_missing=False,
            thumb_format="png",
            collage_format="png",
            thumb_width=640,
            tile_width=320,
            upscale_policy="if_smaller_than",
        )

    # nothing instantiated or processed
    assert len(_FakeThumbWorker.instances) == 0
    assert len(_FakeThumbWorker.process_calls) == 0

    # empty report
    assert getattr(rep, "scanned", None) == 0
    assert getattr(rep, "generated", None) == 0
    assert getattr(rep, "updated", None) == 0
    assert getattr(rep, "skipped", None) == 0
    assert getattr(rep, "errors", None) == 0
