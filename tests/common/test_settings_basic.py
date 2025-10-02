import os
from pathlib import Path
from hexmedia.common.settings import get_settings


def test_settings_dirs_created(tmp_path, monkeypatch):
    # ensure a clean cache per test
    from hexmedia.common import settings as s
    try:
        s.get_settings.cache_clear()
    except Exception:
        # If not cached, ignore
        pass

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))

    cfg = get_settings()
    assert cfg.data_root == tmp_path
    assert cfg.incoming_root.exists()
    assert cfg.media_root.exists()
    assert cfg.processed_root.exists()
    assert cfg.temp_root.exists()

    # spot-check a couple defaults
    assert cfg.ingest_run_limit >= 1
    assert cfg.hexmedia_bucket_max >= 1
