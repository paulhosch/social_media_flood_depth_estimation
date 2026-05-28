#!/usr/bin/env python3
"""Export index.parquet to JSON for the EXIF map web app."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.exif import (
    FLOOD_CLASSIFICATION_COLUMNS,
    FLOOD_DEPTH_COLUMNS,
    INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION,
    INDEX_COLUMNS_WITH_FLOOD_DEPTH,
    geometry_coordinates,
)
from exif_images.flood_depth import parse_detections_json

DEFAULT_IN = ROOT / "data" / "exif_images"
DEFAULT_OUT = ROOT / "web" / "exif-map" / "public" / "data" / "map-index.json"

COORD_DECIMALS = 5
EXPORT_PROFILES = ("internal-full", "public-safe")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _taken_at(original: datetime | None, record: datetime | None) -> datetime | None:
    return original if original is not None else record


def _coord_key(lon: float, lat: float) -> str:
    return f"{round(lon, COORD_DECIMALS):.{COORD_DECIMALS}f},{round(lat, COORD_DECIMALS):.{COORD_DECIMALS}f}"


def _apply_profile(point: dict, profile: str) -> dict:
    if profile == "internal-full":
        return point
    if profile == "public-safe":
        redacted = dict(point)
        redacted["post_id"] = ""
        redacted["caption"] = ""
        redacted["tags"] = []
        return redacted
    raise ValueError(
        f"unsupported profile '{profile}'; expected one of {', '.join(EXPORT_PROFILES)}"
    )


def export(*, in_dir: Path, out_path: Path, profile: str = "internal-full") -> dict:
    parquet_path = in_dir / "index.parquet"
    manifest_path = in_dir / "manifest.json"
    if not parquet_path.is_file():
        raise FileNotFoundError(
            f"missing {parquet_path}; run scripts/build_exif_images.py first"
        )

    if manifest_path.is_file():
        with manifest_path.open(encoding="utf-8") as handle:
            manifest = json.load(handle)
    else:
        manifest = {}

    table = pq.read_table(parquet_path)
    if manifest.get("flood_depth"):
        if table.column_names != list(INDEX_COLUMNS_WITH_FLOOD_DEPTH):
            raise ValueError(
                "manifest records flood_depth but index.parquet "
                f"columns are {table.column_names}; "
                "run scripts/enrich_flood_depth.py"
            )
    elif manifest.get("flood_classification"):
        if table.column_names != list(INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION):
            raise ValueError(
                "manifest records flood_classification but index.parquet "
                f"columns are {table.column_names}; "
                "run scripts/enrich_flood_classification.py"
            )
    has_flood_columns = all(
        name in table.column_names for name in FLOOD_CLASSIFICATION_COLUMNS
    )
    has_flood_depth_columns = all(
        name in table.column_names for name in FLOOD_DEPTH_COLUMNS
    )
    n = table.num_rows

    lons: list[float] = []
    lats: list[float] = []
    coord_keys: list[str] = []

    for i in range(n):
        lon, lat = geometry_coordinates(table.column("geometry")[i].as_py())
        lons.append(lon)
        lats.append(lat)
        coord_keys.append(_coord_key(lon, lat))

    stack_counts = Counter(coord_keys)

    points: list[dict] = []
    taken_times: list[datetime] = []

    for i in range(n):
        original = table.column("exif_taken_at_original")[i].as_py()
        record = table.column("exif_taken_at_record")[i].as_py()
        taken = _taken_at(original, record)
        if taken is not None:
            taken_times.append(taken)

        tags_raw = table.column("tags")[i].as_py()
        try:
            tags = json.loads(tags_raw) if tags_raw else []
        except json.JSONDecodeError:
            tags = []
        if not isinstance(tags, list):
            tags = [str(tags)]

        lon, lat = lons[i], lats[i]
        point = {
            "file_name": table.column("file_name")[i].as_py(),
            "lon": lon,
            "lat": lat,
            "platform": table.column("platform")[i].as_py() or "",
            "post_id": table.column("post_id")[i].as_py() or "",
            "caption": table.column("caption")[i].as_py() or "",
            "tags": tags,
            "exif_taken_at_original": _iso(original),
            "exif_taken_at_record": _iso(record),
            "taken_at": _iso(taken),
            "stack_count": stack_counts[coord_keys[i]],
        }
        if has_flood_columns:
            point["flood_class"] = table.column("flood_class")[i].as_py()
            point["flood_score_flooded"] = float(
                table.column("flood_score_flooded")[i].as_py()
            )
            point["flood_score_non_flooded"] = float(
                table.column("flood_score_non_flooded")[i].as_py()
            )
        if has_flood_depth_columns:
            max_level = table.column("flood_depth_max_level")[i].as_py()
            detections_raw = table.column("flood_depth_detections")[i].as_py()
            detections = parse_detections_json(detections_raw)
            point["flood_depth_max_level"] = (
                int(max_level) if max_level is not None else None
            )
            point["flood_depth_vehicle_count"] = int(
                table.column("flood_depth_vehicle_count")[i].as_py()
            )
            point["flood_depth_high_danger"] = bool(
                table.column("flood_depth_high_danger")[i].as_py()
            )
            point["flood_depth_detections"] = [
                {
                    "level": detection.level,
                    "confidence": detection.confidence,
                    "bbox": list(detection.bbox),
                }
                for detection in detections
            ]
        points.append(_apply_profile(point, profile))

    time_range: dict[str, str | None] = {"min": None, "max": None}
    if taken_times:
        time_range = {
            "min": _iso(min(taken_times)),
            "max": _iso(max(taken_times)),
        }

    payload = {
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "profile": profile,
        "point_count": len(points),
        "time_range": time_range,
        "points": points,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    return {"point_count": len(points), "out_path": str(out_path), "profile": profile}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export data/exif_images/index.parquet for the map web app."
    )
    parser.add_argument(
        "--in-dir",
        type=Path,
        default=DEFAULT_IN,
        help="Directory containing index.parquet",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSON path",
    )
    parser.add_argument(
        "--profile",
        default="internal-full",
        choices=EXPORT_PROFILES,
        help="Export profile: internal-full or public-safe",
    )
    args = parser.parse_args()
    stats = export(in_dir=args.in_dir, out_path=args.out, profile=args.profile)
    print(
        f"Wrote {stats['point_count']} points to {stats['out_path']} "
        f"(profile={stats['profile']})"
    )


if __name__ == "__main__":
    main()
