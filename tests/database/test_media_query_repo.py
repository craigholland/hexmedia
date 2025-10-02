# tests/database/test_media_query_repo.py
from __future__ import annotations

from uuid import uuid4
from sqlalchemy import select

from hexmedia.database.models.media import MediaItem as DBMediaItem, MediaAsset as DBMediaAsset
from hexmedia.database.repos.media_query import MediaQueryRepo
from hexmedia.domain.entities.media_item import MediaIdentity
from hexmedia.domain.enums.media_kind import MediaKind
from hexmedia.domain.enums.asset_kind import AssetKind


def _mk_item(folder: str, name: str, ext: str = "mp4") -> DBMediaItem:
    return DBMediaItem(
        kind=MediaKind.video,
        media_folder=folder,
        identity_name=name,
        video_ext=ext,
        size_bytes=123,
    )


def test_list_and_get_by_identity(db):
    repo = MediaQueryRepo(db)

    a = _mk_item("00", "aaaaaaaaaaaa")
    b = _mk_item("01", "bbbbbbbbbbbb")
    db.add_all([a, b])
    db.flush()

    # list
    out = repo.list_media_items(limit=10, offset=0)
    assert len(out) >= 2
    got = {(x.media_folder, x.identity_name, x.video_ext) for x in out}
    assert ("00", "aaaaaaaaaaaa", "mp4") in got
    assert ("01", "bbbbbbbbbbbb", "mp4") in got

    # by identity (full triplet)
    ident = MediaIdentity(media_folder="00", identity_name="aaaaaaaaaaaa", video_ext="mp4")
    dom = repo.get_by_identity(ident)
    assert dom is not None
    assert dom.media_folder == "00"
    assert dom.identity_name == "aaaaaaaaaaaa"
    assert dom.video_ext == "mp4"


def test_exists_hash(db):
    repo = MediaQueryRepo(db)
    a = _mk_item("02", "cccccccccccc")
    a.hash_sha256 = "deadbeef" * 8
    db.add(a)
    db.flush()

    assert repo.exists_hash("deadbeef" * 8) is True
    assert repo.exists_hash("feedface" * 8) is False


def test_find_video_candidates_for_thumbs_respects_regenerate_and_assets(db):
    """
    When regenerate=False → only items missing either thumb or contact_sheet appear.
    When regenerate=True  → all videos appear.
    """
    # Three items: one has both assets, one has only thumb, one has none
    i_full = _mk_item("10", "fullthumbsheet01")
    i_thumb_only = _mk_item("10", "thumbonly01")
    i_none = _mk_item("10", "noassets01")
    db.add_all([i_full, i_thumb_only, i_none])
    db.flush()

    # Assets for i_full
    db.add_all([
        DBMediaAsset(media_item_id=i_full.id, kind=AssetKind.thumb, rel_path="assets/thumb.png", width=100, height=100),
        DBMediaAsset(media_item_id=i_full.id, kind=AssetKind.contact_sheet, rel_path="assets/contact.png", width=300, height=300),
    ])
    # Asset for i_thumb_only
    db.add(DBMediaAsset(media_item_id=i_thumb_only.id, kind=AssetKind.thumb, rel_path="assets/thumb.png", width=100, height=100))
    db.flush()

    repo = MediaQueryRepo(db)

    # regenerate=False → returns i_thumb_only and i_none
    cands = repo.find_video_candidates_for_thumbs(limit=10, regenerate=False)
    ids = {mid for (mid, _rel, _file) in cands}
    assert str(i_full.id) not in ids
    assert str(i_thumb_only.id) in ids
    assert str(i_none.id) in ids

    # regenerate=True → returns all three
    all_cands = repo.find_video_candidates_for_thumbs(limit=10, regenerate=True)
    all_ids = {mid for (mid, _rel, _file) in all_cands}
    assert {str(i_full.id), str(i_thumb_only.id), str(i_none.id)}.issubset(all_ids)
