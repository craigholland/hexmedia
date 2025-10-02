import pytest
from uuid import uuid4
from hexmedia.domain.entities.media_asset import MediaAsset
from hexmedia.domain.entities.media_artifact import Rating
from hexmedia.domain.enums.asset_kind import AssetKind


def test_media_asset_valid_minimal():
    mi = uuid4()
    a = MediaAsset(
        media_item_id=mi,
        kind=AssetKind.thumb,
        rel_path="assets/thumb.png",
        width=640,
        height=360,
    )
    assert a.media_item_id == mi
    assert a.kind == AssetKind.thumb
    assert a.rel_path.endswith("thumb.png")
    assert a.width == 640 and a.height == 360


@pytest.mark.parametrize("w,h", [(-1, 10), (10, -1), (-5, -5)])
def test_media_asset_disallow_negative_dimensions(w, h):
    with pytest.raises(ValueError):
        MediaAsset(
            media_item_id=uuid4(),
            kind=AssetKind.contact_sheet,
            rel_path="assets/contact_sheet.png",
            width=w,
            height=h,
        )


@pytest.mark.parametrize("bad_rel", ["", "  ", None])
def test_media_asset_requires_rel_path(bad_rel):
    with pytest.raises(ValueError):
        MediaAsset(
            media_item_id=uuid4(),
            kind=AssetKind.thumb,
            rel_path=bad_rel,  # type: ignore[arg-type]
        )


def test_rating_valid_bounds():
    r = Rating(media_item_id=uuid4(), score=5)
    assert r.score == 5


@pytest.mark.parametrize("bad", [-1, 6])
def test_rating_out_of_bounds(bad):
    with pytest.raises(ValueError):
        Rating(media_item_id=uuid4(), score=bad)


def test_rating_must_be_int():
    with pytest.raises(ValueError):
        Rating(media_item_id=uuid4(), score=4.5)  # type: ignore[arg-type]


def test_rating_requires_media_item_id():
    with pytest.raises(ValueError):
        Rating(media_item_id=None, score=3)  # type: ignore[arg-type]
