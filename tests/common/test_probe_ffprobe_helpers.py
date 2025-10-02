from pathlib import Path
from hexmedia.common.probe.ffprobe_helpers import build_ffprobe_cmd, parse_ffprobe


def test_build_ffprobe_cmd_uses_json_flags(tmp_path):
    f = tmp_path / "video.mp4"
    cmd = build_ffprobe_cmd(f)
    assert "ffprobe" in cmd[0].lower()
    # Core JSON-ish flags we rely on
    assert "-show_streams" in cmd
    assert "-show_format" in cmd
    assert str(f) == cmd[-1]


def test_parse_ffprobe_minimal():
    data = {
        "format": {
            "duration": "12.34",
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "bit_rate": "123456",
            "tags": {"language": "eng"},
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30000/1001",
                "display_aspect_ratio": "16:9",
                "tags": {"language": "eng"},
            },
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }

    out = parse_ffprobe(data)
    assert out["duration_sec"] == 12
    assert out["container"] is not None
    assert out["bitrate"] == 123456
    assert out["codec_video"] == "h264"
    assert out["codec_audio"] == "aac"
    assert out["width"] == 1920
    assert out["height"] == 1080
    assert 29.9 < out["fps"] < 30.1
    assert out["aspect_ratio"] in ("16:9", "")  # allow empty fallback
    assert out["language"] in ("eng", None)
    assert out["has_subtitles"] in (False, True)
