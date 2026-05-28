"""Read EXIF GPS and datetime from JPEG bytes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

TAG_DATETIME = 306
TAG_DATETIME_ORIGINAL = 36867
EXIF_IFD = 0x8769
GPS_IFD = 0x8825

INDEX_COLUMNS: tuple[str, ...] = (
    "file_name",
    "platform",
    "post_id",
    "caption",
    "tags",
    "exif_taken_at_original",
    "exif_taken_at_record",
    "geometry",
)

FLOOD_CLASSIFICATION_COLUMNS: tuple[str, ...] = (
    "flood_class",
    "flood_score_flooded",
    "flood_score_non_flooded",
)

INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION: tuple[str, ...] = (
    *INDEX_COLUMNS,
    *FLOOD_CLASSIFICATION_COLUMNS,
)

FLOOD_DEPTH_COLUMNS: tuple[str, ...] = (
    "flood_depth_max_level",
    "flood_depth_vehicle_count",
    "flood_depth_high_danger",
    "flood_depth_detections",
)

INDEX_COLUMNS_WITH_FLOOD_DEPTH: tuple[str, ...] = (
    *INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION,
    *FLOOD_DEPTH_COLUMNS,
)

FLOOD_CLASS_VALUES: frozenset[str] = frozenset({"flooded", "non_flooded"})


@dataclass(frozen=True)
class ExifRecord:
    """Parsed EXIF fields used for inclusion, Parquet, and re-embed."""

    lon: float
    lat: float
    geometry: str
    taken_at_original: datetime | None
    taken_at_record: datetime | None
    datetime_original_raw: str | None
    datetime_record_raw: str | None


def _rational_to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, tuple) and len(value) == 2:
        num, den = value
        if not den:
            return 0.0
        return float(num) / float(den)
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _dms_to_decimal(dms: tuple[Any, Any, Any]) -> float:
    degrees, minutes, seconds = (_rational_to_float(v) for v in dms)
    return degrees + minutes / 60.0 + seconds / 3600.0


def parse_gps_point(gps_ifd: dict[int, Any]) -> tuple[float, float] | None:
    """Return (lon, lat) in WGS-84 decimal degrees, or None if not parseable."""
    lat_dms = gps_ifd.get(2)
    lon_dms = gps_ifd.get(4)
    if not lat_dms or not lon_dms:
        return None

    lat = _dms_to_decimal(lat_dms)
    lon = _dms_to_decimal(lon_dms)

    lat_ref = gps_ifd.get(1)
    lon_ref = gps_ifd.get(3)
    if lat_ref in (b"S", "S"):
        lat = -lat
    elif lat_ref not in (b"N", "N", None):
        return None

    if lon_ref in (b"W", "W"):
        lon = -lon
    elif lon_ref not in (b"E", "E", None):
        return None

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if not (abs(lat) < float("inf") and abs(lon) < float("inf")):
        return None

    return lon, lat


def to_geometry_geojson(lon: float, lat: float) -> str:
    return json.dumps(
        {"type": "Point", "coordinates": [lon, lat]},
        separators=(",", ":"),
    )


def _decode_exif_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace").strip("\x00")
    else:
        text = str(value).strip()
    return text or None


def parse_exif_datetime(value: Any) -> datetime | None:
    """Parse EXIF datetime string YYYY:MM:DD HH:MM:SS to UTC."""
    text = _decode_exif_string(value)
    if not text:
        return None
    try:
        parsed = datetime.strptime(text, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _get_exif_tag(exif: Any, tag_id: int) -> Any:
    value = exif.get(tag_id)
    if value is not None:
        return value
    if not hasattr(exif, "get_ifd"):
        return None
    try:
        exif_ifd = exif.get_ifd(EXIF_IFD)
    except (KeyError, TypeError):
        return None
    return exif_ifd.get(tag_id)


def parse_exif_datetimes(
    exif: Any,
) -> tuple[datetime | None, datetime | None, str | None, str | None]:
    original_value = _get_exif_tag(exif, TAG_DATETIME_ORIGINAL)
    record_value = exif.get(TAG_DATETIME)
    original_raw = _decode_exif_string(original_value)
    record_raw = _decode_exif_string(record_value)
    original = parse_exif_datetime(original_value)
    record = parse_exif_datetime(record_value)
    return original, record, original_raw, record_raw


def classify_jpeg_bytes(data: bytes) -> str:
    """
    Classify a JPEG without building a full record.

    Returns one of: corrupt, gps_stub, no_qualify, included.
    """
    if len(data) < 100:
        return "corrupt"

    try:
        image = Image.open(BytesIO(data))
        exif = image.getexif()
    except Exception:
        return "corrupt"

    if not exif:
        return "no_qualify"

    gps_ifd = exif.get_ifd(GPS_IFD) if hasattr(exif, "get_ifd") else None
    if not gps_ifd:
        return "no_qualify"

    if not gps_ifd.get(2) or not gps_ifd.get(4):
        return "gps_stub"

    if read_exif_from_bytes(data) is None:
        return "no_qualify"
    return "included"


def read_exif_from_bytes(data: bytes) -> ExifRecord | None:
    """
    Parse inclusion-qualified EXIF from JPEG bytes.

    Returns None when GPS or datetime rules fail.
    """
    if len(data) < 100:
        return None

    try:
        image = Image.open(BytesIO(data))
        exif = image.getexif()
    except Exception:
        return None

    if not exif:
        return None

    gps_ifd = exif.get_ifd(GPS_IFD) if hasattr(exif, "get_ifd") else None
    if not gps_ifd:
        return None

    point = parse_gps_point(gps_ifd)
    if point is None:
        return None

    lon, lat = point
    original, record, original_raw, record_raw = parse_exif_datetimes(exif)
    if original is None and record is None:
        return None

    return ExifRecord(
        lon=lon,
        lat=lat,
        geometry=to_geometry_geojson(lon, lat),
        taken_at_original=original,
        taken_at_record=record,
        datetime_original_raw=original_raw,
        datetime_record_raw=record_raw,
    )


def geometry_coordinates(geometry: str) -> tuple[float, float]:
    """Return (lon, lat) from a GeoJSON Point geometry string."""
    payload = json.loads(geometry)
    if payload.get("type") != "Point":
        raise ValueError("expected GeoJSON Point")
    lon, lat = payload["coordinates"]
    return float(lon), float(lat)
