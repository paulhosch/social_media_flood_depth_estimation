"""Resize JPEGs and re-embed minimal EXIF."""

from __future__ import annotations

from io import BytesIO

import piexif
from PIL import Image

from exif_images.exif import ExifRecord

Image.MAX_IMAGE_PIXELS = None


def _decimal_to_dms_rational(value: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    value = abs(value)
    degrees = int(value)
    minutes_float = (value - degrees) * 60.0
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60.0
    return ((degrees, 1), (minutes, 1), (int(round(seconds * 10000)), 10000))


def _exif_datetime_bytes(raw: str | None) -> bytes | None:
    if not raw:
        return None
    return raw.encode("ascii")


def build_piexif_dict(record: ExifRecord) -> dict[str, dict]:
    """Build piexif dict with GPS and whichever datetime tags were present."""
    zeroth: dict = {}
    exif_ifd: dict = {}
    gps_ifd: dict = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if record.lat >= 0 else b"S",
        piexif.GPSIFD.GPSLatitude: _decimal_to_dms_rational(record.lat),
        piexif.GPSIFD.GPSLongitudeRef: b"E" if record.lon >= 0 else b"W",
        piexif.GPSIFD.GPSLongitude: _decimal_to_dms_rational(record.lon),
    }

    original_bytes = _exif_datetime_bytes(record.datetime_original_raw)
    record_bytes = _exif_datetime_bytes(record.datetime_record_raw)

    if original_bytes:
        exif_ifd[piexif.ExifIFD.DateTimeOriginal] = original_bytes
    if record_bytes:
        zeroth[piexif.ImageIFD.DateTime] = record_bytes
        if piexif.ExifIFD.DateTimeOriginal not in exif_ifd:
            exif_ifd[piexif.ExifIFD.DateTimeDigitized] = record_bytes

    out: dict[str, dict] = {"GPS": gps_ifd}
    if zeroth:
        out["0th"] = zeroth
    if exif_ifd:
        out["Exif"] = exif_ifd
    return out


def prepare_output_jpeg(
    original_bytes: bytes,
    record: ExifRecord,
    *,
    max_dimension: int = 2048,
    jpeg_quality: int = 85,
) -> bytes:
    """Decode, resize (longest edge), re-encode JPEG with re-embedded EXIF."""
    image = Image.open(BytesIO(original_bytes))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    exif_dict = build_piexif_dict(record)
    exif_bytes = piexif.dump(exif_dict)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=jpeg_quality, exif=exif_bytes)
    return buffer.getvalue()
