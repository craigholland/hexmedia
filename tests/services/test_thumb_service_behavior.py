import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import sessionmaker

import hexmedia.services.ingest.thumb_service as svc_mod
from hexmedia.services.ingest.thumb_service import ThumbService
from hexmedia.database.repos.media_query import MediaQueryRepo


# ----- Shared fake worker -----------------------------------------------------

class _FakeWorker:
    instances: List["_FakeWorker"] = []
    ctor_args: List[Dict[str, Any]] = []
    process_calls: List[Tuple[str, str, str]] = []
    # behavior map: index -> either dict result or Exception to raise
    scripted_results: Dict[int, Any] = {}

    def __init__(self, **kwargs):
        type(self).instances.append(self)
        type(self).ctor_args.append(dict(kwargs))

    def process_one(self, media_item_id: str, rel_dir: str, fname: str):
        i = len(type(self).process_calls)
        type(self).process_calls.append((media_item_id, rel_dir, fname))
        if i in type(self).scripted_results:
            val = type(self).scripted_results[i]
            if isinstance(val, Exception):
                raise val
            return val
        # default happy-path single unit of work
        return {"generated": 1, "updated": 1, "skipped": 0, "errors": 0}

    # helpers to reset between tests
    @classmethod
    def _reset(cls):
        cls.instances.clear()
        cls.ctor_args.clear()
        cls.process_calls.clear()
        cls.scripted_results.clear()


# ----- Test 1: aggregates errors/details & counts properly --------------------

def test_thumb_service_aggregates_errors_and_details(monkeypatch, db_engine):
    _FakeWorker._reset()
    monkeypatch.setattr(svc_mod, "ThumbWorker", _FakeWorker, raising=True)

    # 3 candidates; worker will: ok, boom, ok  => errors = 1
    def _fake_candidates(self, *, limit: int, regenerate: bool):
        return [
            (str(uuid.uuid4()), "00/one", "one.mp4"),
            (str(uuid.uuid4()), "00/two", "two.mp4"),
            (str(uuid.uuid4()), "01/three", "three.mp4"),
        ]

    monkeypatch.setattr(
        MediaQueryRepo, "find_video_candidates_for_thumbs", _fake_candidates, raising=True
    )

    # script results: index 1 raises
    _FakeWorker.scripted_results = {
        1: RuntimeError("boom"),
    }

    # small custom config to ensure deterministic defaults if used
    cfg = SimpleNamespace(
        media_root=None,
        thumb_format="jpg",
        collage_format="png",
        thumb_width=480,
        collage_tile_width=160,
        upscale_policy="never",
        max_thumb_workers=4,
    )

    SessionLocal = sessionmaker(bind=db_engine, future=True)
    with SessionLocal() as db:
        svc = ThumbService(db)
        # inject config to avoid depending on env
        svc.cfg = cfg  # type: ignore[attr-defined]

        rep = svc.run(
            limit=10,
            regenerate=False,
            workers=3,
            include_missing=False,
            thumb_format="jpg",
            collage_format="png",
            thumb_width=480,
            tile_width=160,
            upscale_policy="never",
        )

    # scanned = number of candidates; 2 successes -> generated/updated=2
    assert rep.scanned == 3
    assert rep.generated == 2
    assert rep.updated == 2
    assert rep.skipped == 0
    assert rep.errors == 1
    assert len(rep.error_details) >= 1
    assert any("boom" in str(e) for e in rep.error_details)


# ----- Test 2: respects max_thumb_workers cap --------------------------------

class _FakeFuture:
    def __init__(self, result):
        self._result = result
    def result(self):
        return self._result

class _CapturingExecutor:
    """Minimal executor stand-in that records max_workers and runs tasks synchronously."""
    captured_max_workers: List[int] = []

    def __init__(self, max_workers: int):
        type(self).captured_max_workers.append(max_workers)
        self._futures: List[_FakeFuture] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        # run immediately, capture the result
        try:
            res = fn(*args, **kwargs)
        except Exception as e:
            res = e  # let test-side as_completed shim raise via result()
        fut = _FakeFuture(res)
        self._futures.append(fut)
        return fut

def _as_completed_passthrough(futures):
    # yield futures as-is; _FakeFuture.result() returns either dict or Exception
    for f in futures:
        # emulate real as_completed behavior: if the stored value is an exception,
        # .result() should raise when called (handled by service)
        yield f

def test_thumb_service_respects_max_workers_cap(monkeypatch, db_engine):
    _FakeWorker._reset()
    monkeypatch.setattr(svc_mod, "ThumbWorker", _FakeWorker, raising=True)

    # override ThreadPoolExecutor & as_completed used in the service module
    monkeypatch.setattr(svc_mod, "ThreadPoolExecutor", _CapturingExecutor, raising=True)
    monkeypatch.setattr(svc_mod, "as_completed", _as_completed_passthrough, raising=True)

    # pretend there are many candidates; we only need a handful
    def _fake_candidates(self, *, limit: int, regenerate: bool):
        return [(str(uuid.uuid4()), "00/one", "one.mp4")] * 5

    monkeypatch.setattr(
        MediaQueryRepo, "find_video_candidates_for_thumbs", _fake_candidates, raising=True
    )

    cfg = SimpleNamespace(
        media_root=None,
        thumb_format="jpg",
        collage_format="png",
        thumb_width=320,
        collage_tile_width=160,
        upscale_policy="never",
        max_thumb_workers=2,  # cap here
    )

    SessionLocal = sessionmaker(bind=db_engine, future=True)
    with SessionLocal() as db:
        svc = ThumbService(db)
        svc.cfg = cfg  # type: ignore[attr-defined]
        svc.run(
            limit=5,
            regenerate=False,
            workers=50,               # huge ask, should be capped to 2
            include_missing=False,
            thumb_format="jpg",
            collage_format="png",
            thumb_width=320,
            tile_width=160,
            upscale_policy="never",
        )

    # verify cap respected
    assert _CapturingExecutor.captured_max_workers == [2]
    # and we still processed all candidates (synchronously in our fake)
    assert len(_FakeWorker.process_calls) == 5


# ----- Test 3: uses config defaults when options are missing ------------------

def test_thumb_service_uses_config_defaults_when_options_missing(monkeypatch, db_engine):
    _FakeWorker._reset()
    monkeypatch.setattr(svc_mod, "ThumbWorker", _FakeWorker, raising=True)

    # exactly one candidate
    def _fake_candidates(self, *, limit: int, regenerate: bool):
        return [(str(uuid.uuid4()), "42/xyz", "xyz.mkv")]

    monkeypatch.setattr(
        MediaQueryRepo, "find_video_candidates_for_thumbs", _fake_candidates, raising=True
    )

    # set defaults in cfg; run() will receive "empty" values and should fall back
    cfg = SimpleNamespace(
        media_root=None,
        thumb_format="defthumb",
        collage_format="defcollage",
        thumb_width=111,
        collage_tile_width=222,
        upscale_policy="defpolicy",
        max_thumb_workers=8,
    )

    SessionLocal = sessionmaker(bind=db_engine, future=True)
    with SessionLocal() as db:
        svc = ThumbService(db)
        svc.cfg = cfg  # type: ignore[attr-defined]

        rep = svc.run(
            limit=1,
            regenerate=True,
            workers=None,          # None -> will default to 1 (then bounded by max_thumb_workers)
            include_missing=True,  # pass-through to worker
            thumb_format="",       # falsy -> use cfg.thumb_format
            collage_format=None,   # None -> use thumb_format or cfg.collage_format
            thumb_width=0,         # 0 -> use cfg.thumb_width
            tile_width=0,          # 0 -> use cfg.collage_tile_width
            upscale_policy="",     # falsy -> cfg.upscale_policy
        )

    # worker constructed with cfg defaults
    assert len(_FakeWorker.instances) == 1
    ctor = _FakeWorker.ctor_args[0]
    assert ctor["regenerate"] is True
    assert ctor["include_missing"] is True
    assert ctor["thumb_format"] == "defthumb"
    assert ctor["collage_format"] == "defcollage"
    assert ctor["thumb_width"] == 111
    assert ctor["tile_width"] == 222
    assert ctor["upscale_policy"] == "defpolicy"

    # basic report sanity (one candidate processed)
    assert rep.scanned == 1
    assert rep.generated == 1
    assert rep.updated == 1
    assert rep.errors == 0
