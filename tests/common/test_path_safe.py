import pytest
from pathlib import Path
from hexmedia.common.path.safe import resolve_root, safe_join, ensure_inside


def test_resolve_root(tmp_path):
    p = resolve_root(tmp_path)
    assert isinstance(p, Path)
    assert p.exists()


def test_safe_join_inside(tmp_path):
    root = tmp_path
    rel = Path("a/b/c.txt")
    out = safe_join(root, rel)
    assert out.parent == root / "a" / "b"
    assert str(out).startswith(str(root))


def test_safe_join_escapes_rejected(tmp_path):
    root = tmp_path
    with pytest.raises(ValueError):
        safe_join(root, "../outside.txt")


def test_ensure_inside_ok(tmp_path):
    inner = tmp_path / "x" / "y"
    inner.mkdir(parents=True, exist_ok=True)
    ensure_inside(inner, tmp_path)  # should not raise


def test_ensure_inside_reject(tmp_path):
    with pytest.raises(ValueError):
        ensure_inside("/tmp", tmp_path)
