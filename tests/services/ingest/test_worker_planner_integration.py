# tests/services/ingest/test_worker_planner_integration.py
from pathlib import Path
from hexmedia.services.ingest.worker import IngestWorker

def test_worker_with_real_planner_dry_run(tmp_path, db):
    f1 = tmp_path / "a.mp4"; f1.write_bytes(b"x")
    f2 = tmp_path / "b.jpg"; f2.write_bytes(b"y")  # any allowed ext is fine

    worker = IngestWorker(db)  # uses real DomainIngestPlanner by default
    rpt = worker.run([f1, f2], dry_run=True)

    assert rpt.error_details == []
    assert rpt.planned_items is not None
    assert len(rpt.planned_items) == 2
