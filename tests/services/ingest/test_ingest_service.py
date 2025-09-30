# tests/services/ingest/test_ingest_service.py
from __future__ import annotations

from pathlib import Path


def _touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"dummy")
    return p


def test_run_calls_worker_and_returns_report(monkeypatch, tmp_path, db):
    """IngestService.run should delegate to IngestWorker and return its report."""
    files = [
        _touch(tmp_path / "a.mp4"),
        _touch(tmp_path / "b.mov"),
    ]

    captured: dict = {}

    class FakeWorker:
        def __init__(self, *args, **kwargs):
            # capture constructor args if you later want to assert DI wiring
            captured["worker_kwargs"] = kwargs

        def run(self, files_in, *, dry_run: bool = False):
            from hexmedia.domain.dataclasses.reports import IngestReport

            captured["files"] = [str(p) for p in files_in]
            captured["dry_run"] = dry_run

            rpt = IngestReport()
            rpt.start()
            rpt.items.append({"ok": True})
            rpt.stop()
            return rpt

    # Monkeypatch the worker used by the service module
    import hexmedia.services.ingest.service as svcmod

    monkeypatch.setattr(svcmod, "IngestWorker", FakeWorker)

    svc = svcmod.IngestService(db)
    report = svc.run(files, dry_run=True)

    assert captured["dry_run"] is True
    # basic shape of the report
    assert getattr(report, "started_at") is not None
    assert getattr(report, "finished_at") is not None
    assert getattr(report, "error_details") == []
    assert getattr(report, "items") and report.items[0]["ok"] is True


def test_run_returns_report_with_errors(monkeypatch, tmp_path, db):
    """If the worker produces an error report, the service should pass it through unchanged."""
    files = [_touch(tmp_path / "bad.mp4")]

    class FakeWorker:
        def __init__(self, *_, **__):
            pass

        def run(self, *_args, **_kwargs):
            from hexmedia.domain.dataclasses.reports import IngestReport

            rpt = IngestReport()
            rpt.start()
            rpt.add_error("boom: simulated failure")
            rpt.stop()
            return rpt

    import hexmedia.services.ingest.service as svcmod

    monkeypatch.setattr(svcmod, "IngestWorker", FakeWorker)

    svc = svcmod.IngestService(db)
    report = svc.run(files, dry_run=False)

    assert report.error_details, "expected an error to be propagated on the report"
    assert "simulated failure" in report.error_details[0]


def test_run_passes_files_through_unchanged(monkeypatch, tmp_path, db):
    """Make sure the exact file paths given to the service reach the worker."""
    files = [
        _touch(tmp_path / "nested" / "x.mp4"),
        _touch(tmp_path / "y.mov"),
    ]

    received = {}

    class FakeWorker:
        def __init__(self, *_, **__):
            pass

        def run(self, files_in, *, dry_run=False):
            from hexmedia.domain.dataclasses.reports import IngestReport

            received["files_in"] = [Path(p) for p in files_in]
            rpt = IngestReport()
            rpt.start()
            rpt.stop()
            return rpt

    import hexmedia.services.ingest.service as svcmod

    monkeypatch.setattr(svcmod, "IngestWorker", FakeWorker)

    svc = svcmod.IngestService(db)
    _ = svc.run(files, dry_run=False)

    assert [p.resolve() for p in received["files_in"]] == [p.resolve() for p in files]
