import pytest
from hexmedia.domain.entities.media_item import MediaIdentity, MediaItem
from hexmedia.domain.enums.media_kind import MediaKind


def test_media_item_construct_with_triplet_initvars_ok():
    """
    Ensure the InitVar path (media_folder_in/identity_name_in/video_ext_in)
    properly hydrates a MediaIdentity and all identity helpers work.
    """
    item = MediaItem(
        kind=MediaKind.video,
        media_folder_in="123",
        identity_name_in="abc123def456",
        video_ext_in="mp4",
        size_bytes=42,
    )

    # identity proxies should be present and correct
    assert item.identity.media_folder == "123"
    assert item.identity.identity_name == "abc123def456"
    assert item.identity.video_ext == "mp4"

    # helper methods
    assert item.identity_key() == ("123", "abc123def456", "mp4")
    assert item.video_rel_path() == "123/abc123def456/abc123def456.mp4"
    assert item.assets_rel_dir() == "123/abc123def456/assets"

    # curation defaults still sane
    assert item.watched is False
    assert item.favorite is False


@pytest.mark.parametrize(
    "kw",
    [
        # missing all
        {},
        # missing two
        {"media_folder_in": "000"},
        {"identity_name_in": "abc123def456"},
        {"video_ext_in": "mp4"},
        # missing one
        {"media_folder_in": "000", "identity_name_in": "abc123def456"},
        {"media_folder_in": "000", "video_ext_in": "mp4"},
        {"identity_name_in": "abc123def456", "video_ext_in": "mp4"},
    ],
)
def test_media_item_requires_full_triplet_when_using_initvars(kw):
    """
    When identity is None, the InitVar hydration requires the full triplet.
    Any partial set should raise ValueError.
    """
    with pytest.raises(ValueError):
        MediaItem(kind=MediaKind.video, **kw)  # no identity, partial triplet -> error


def test_media_item_requires_identity_or_triplet_still_holds():
    """
    The previous expectation remains: with neither identity nor InitVars, raise ValueError.
    """
    with pytest.raises(ValueError):
        MediaItem(kind=MediaKind.video)  # type: ignore[call-arg]


def test_media_item_construct_with_explicit_identity_still_ok():
    """
    The explicit identity path should remain fully supported.
    """
    ident = MediaIdentity(media_folder="777", identity_name="ffffffffffff", video_ext="mkv")
    item = MediaItem(kind=MediaKind.video, identity=ident, size_bytes=1)
    assert item.identity_key() == ("777", "ffffffffffff", "mkv")
    assert item.video_rel_path() == "777/ffffffffffff/ffffffffffff.mkv"


def test_media_identity_paths_and_key():
    ident = MediaIdentity(media_folder="000", identity_name="abc123def456", video_ext="mp4")
    assert ident.video_filename() == "abc123def456.mp4"
    assert ident.rel_dir() == "000/abc123def456"
    assert ident.video_rel_path() == "000/abc123def456/abc123def456.mp4"
    assert ident.assets_rel_dir() == "000/abc123def456/assets"
    assert ident.as_key() == ("000", "abc123def456", "mp4")
    d = ident.as_dict()
    assert d["media_folder"] == "000" and d["identity_name"] == "abc123def456" and d["video_ext"] == "mp4"


def test_media_item_construct_with_identity_ok():
    ident = MediaIdentity(media_folder="001", identity_name="ffffffffffff", video_ext="mkv")
    item = MediaItem(kind=MediaKind.video, identity=ident, size_bytes=123)
    # identity passthrough helpers
    assert item.identity_key() == ("001", "ffffffffffff", "mkv")
    assert item.video_rel_path() == "001/ffffffffffff/ffffffffffff.mkv"
    assert item.assets_rel_dir() == "001/ffffffffffff/assets"
    # a couple of default flags
    assert item.watched is False
    assert item.favorite is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("size_bytes", -1),
        ("width", -1),
        ("height", -1),
        ("duration_sec", -1),
        ("bitrate", -1),
    ],
)
def test_media_item_invariants_disallow_negatives(field, value):
    ident = MediaIdentity(media_folder="002", identity_name="111111111111", video_ext="mp4")
    kwargs = dict(kind=MediaKind.video, identity=ident, size_bytes=0)
    kwargs[field] = value
    with pytest.raises(ValueError):
        MediaItem(**kwargs)


def test_media_item_requires_identity_or_triplet():
    # No identity and no triplet -> error
    with pytest.raises(ValueError):
        MediaItem(kind=MediaKind.video)  # type: ignore[call-arg]
