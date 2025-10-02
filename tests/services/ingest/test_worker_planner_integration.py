# tests/services/ingest/test_worker_planner_integration.py
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from hexmedia.services.ingest.worker import IngestWorker

def test_worker_with_real_planner_dry_run(tmp_path, db):
    SessionLocal = sessionmaker(bind=db, future=True)
    with SessionLocal() as session:
        f1 = tmp_path / "a.mp4"
        f1.write_bytes(b"x")
        f2 = tmp_path / "b.jpg"
        f2.write_bytes(b"y")

        worker = IngestWorker(session)  # pass a Session, not Engine
        rpt = worker.run([f1, f2], dry_run=True)

        assert rpt.planned_items is not None
        assert len(rpt.planned_items) == 2
        assert rpt.error_details == []
