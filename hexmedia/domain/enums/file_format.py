# hexmedia/domain/enums/file_format.py
from __future__ import annotations

from enum import StrEnum


class VideoFormats(StrEnum):
    MP4 = "mp4"
    MKV = "mkv"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"
    M4V = "m4v"
    MPEG = "mpeg"
    MPG = "mpg"
    TS = "ts"
    M2TS = "m2ts"
    FLV = "flv"


class ImageFormats(StrEnum):
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"
    BMP = "bmp"
    TIFF = "tiff"
    TIF = "tif"
    AVIF = "avif"
