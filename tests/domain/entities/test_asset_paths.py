from hexmedia.domain.policies.asset_paths import asset_relative_paths, preferred_collage_grid


def test_asset_relative_paths_default_names():
    ap = asset_relative_paths(thumb_fmt="png", sheet_fmt="png")
    assert ap["thumb"] == "assets/thumb.png"
    assert ap["contact_sheet"] == "assets/contact_sheet.png"


def test_preferred_collage_grid_nine_tiles():
    assert preferred_collage_grid(9) == (3, 3)


def test_preferred_collage_grid_general():
    # A rough square heuristic; we don't assert exact values, just shape
    r, c = preferred_collage_grid(7)
    assert r * c >= 7
    assert abs(r - c) <= 2
