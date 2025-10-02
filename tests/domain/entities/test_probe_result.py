from hexmedia.domain.entities.probe import ProbeResult


def test_probe_result_dataclass_defaults():
    pr = ProbeResult()
    assert pr.duration_sec is None
    assert pr.has_subtitles is False

    pr2 = ProbeResult(duration_sec=120, width=1920, height=1080, fps=23.976)
    assert pr2.duration_sec == 120
    assert pr2.width == 1920
    assert pr2.height == 1080
    assert 23.9 > pr2.fps > 23.9 - 0.1 or 24.1 > pr2.fps > 24.0 - 0.1  # loose-ish check
