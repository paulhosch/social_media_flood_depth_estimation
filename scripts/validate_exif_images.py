#!/usr/bin/env python3
"""Validate the built exif_images dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.exif import (
    FLOOD_CLASS_VALUES,
    INDEX_COLUMNS,
    INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION,
    INDEX_COLUMNS_WITH_FLOOD_DEPTH,
    geometry_coordinates,
    read_exif_from_bytes,
)
from exif_images.flood_classification import (
    FLOOD_CLASS_FLOODED,
    FLOOD_CLASS_NON_FLOODED,
)
from exif_images.flood_depth import HIGH_DANGER_LEVELS, parse_detections_json
from exif_images.paths import IMAGES_SUBDIR, image_path, images_dir

Image.MAX_IMAGE_PIXELS = None

DEFAULT_OUT = ROOT / "data" / "exif_images"
COORD_TOLERANCE = 1e-6


def _check_geometry(geometry: str) -> tuple[float, float]:
    lon, lat = geometry_coordinates(geometry)
    payload = json.loads(geometry)
    if payload.get("type") != "Point":
        raise ValueError("geometry must be GeoJSON Point")
    coords = payload.get("coordinates")
    if not isinstance(coords, list) or len(coords) != 2:
        raise ValueError("geometry coordinates must be [lon, lat]")
    return lon, lat


def _normalize_timestamp(value):
    if value is None:
        return None
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    return value


def _datetimes_match(stored, parsed) -> bool:
    stored_norm = _normalize_timestamp(stored)
    if stored_norm is None and parsed is None:
        return True
    if stored_norm is None or parsed is None:
        return False
    return stored_norm == parsed


def _check_no_within_post_duplicate_content(
    *,
    out_dir: Path,
    images_subdir: str,
    platforms: list[str],
    post_ids: list[str],
    file_names: list[str],
) -> list[str]:
    """Fail when a post includes multiple on-disk JPEGs with identical content."""
    errors: list[str] = []
    by_post: dict[tuple[str, str], list[str]] = defaultdict(list)
    for platform, post_id, file_name in zip(platforms, post_ids, file_names, strict=True):
        if not post_id:
            continue
        by_post[(platform, post_id)].append(file_name)

    for (platform, post_id), names in by_post.items():
        if len(names) < 2:
            continue
        hashes: dict[str, list[str]] = defaultdict(list)
        for file_name in names:
            jpg_path = image_path(out_dir, file_name, subdir=images_subdir)
            if not jpg_path.is_file():
                continue
            digest = hashlib.sha256(jpg_path.read_bytes()).hexdigest()
            hashes[digest].append(file_name)

        for digest, dup_names in hashes.items():
            if len(dup_names) > 1:
                errors.append(
                    f"{platform}/{post_id}: duplicate content hash {digest[:12]} "
                    f"for {len(dup_names)} images"
                )
    return errors


def validate(
    *,
    out_dir: Path,
    sample: int | None,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    manifest_path = out_dir / "manifest.json"
    parquet_path = out_dir / "index.parquet"

    if not manifest_path.is_file():
        errors.append(f"missing {manifest_path}")
        return False, errors
    if not parquet_path.is_file():
        errors.append(f"missing {parquet_path}")
        return False, errors

    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    images_subdir = manifest.get("images_subdir", IMAGES_SUBDIR)

    has_flood_classification = manifest.get("flood_classification") is not None
    has_flood_depth = manifest.get("flood_depth") is not None
    if has_flood_depth:
        expected_columns = INDEX_COLUMNS_WITH_FLOOD_DEPTH
    elif has_flood_classification:
        expected_columns = INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION
    else:
        expected_columns = INDEX_COLUMNS

    table = pq.read_table(parquet_path)
    columns = table.column_names
    if columns != list(expected_columns):
        errors.append(f"unexpected columns: {columns}")

    file_names = table.column("file_name").to_pylist()
    jpg_names = {
        path.name for path in images_dir(out_dir, subdir=images_subdir).glob("*.jpg")
    }
    parquet_names = set(file_names)

    if jpg_names != parquet_names:
        only_jpg = jpg_names - parquet_names
        only_parquet = parquet_names - jpg_names
        if only_jpg:
            errors.append(f"jpgs without parquet rows: {len(only_jpg)}")
        if only_parquet:
            errors.append(f"parquet rows without jpgs: {len(only_parquet)}")

    errors.extend(
        _check_no_within_post_duplicate_content(
            out_dir=out_dir,
            images_subdir=images_subdir,
            platforms=table.column("platform").to_pylist(),
            post_ids=table.column("post_id").to_pylist(),
            file_names=file_names,
        )
    )

    row_count = table.num_rows
    expected_count = manifest.get("included_count")
    if expected_count is not None and row_count != expected_count:
        errors.append(
            f"row count {row_count} != manifest.included_count {expected_count}"
        )

    max_dim = manifest.get("image_processing", {}).get("max_dimension_px", 2048)
    limit = row_count if sample is None else min(sample, row_count)

    col = {name: table.column(name).to_pylist() for name in expected_columns}

    for index in range(limit):
        file_name = col["file_name"][index]
        geometry = col["geometry"][index]
        taken_original = col["exif_taken_at_original"][index]
        taken_record = col["exif_taken_at_record"][index]

        try:
            _check_geometry(geometry)
        except ValueError as exc:
            errors.append(f"{file_name}: {exc}")
            continue

        if taken_original is None and taken_record is None:
            errors.append(f"{file_name}: no datetime in parquet row")

        jpg_path = image_path(out_dir, file_name, subdir=images_subdir)
        if not jpg_path.is_file():
            errors.append(f"{file_name}: missing jpg")
            continue

        try:
            with Image.open(jpg_path) as image:
                width, height = image.size
        except Exception as exc:
            errors.append(f"{file_name}: cannot open jpg ({exc})")
            continue

        if max(width, height) > max_dim:
            errors.append(
                f"{file_name}: longest edge {max(width, height)} > {max_dim}"
            )

        record = read_exif_from_bytes(jpg_path.read_bytes())
        if record is None:
            errors.append(f"{file_name}: EXIF no longer qualifies after build")
            continue

        parquet_lon, parquet_lat = geometry_coordinates(geometry)
        if (
            abs(record.lon - parquet_lon) > COORD_TOLERANCE
            or abs(record.lat - parquet_lat) > COORD_TOLERANCE
        ):
            errors.append(f"{file_name}: geometry mismatch vs re-read EXIF")

        if not _datetimes_match(taken_original, record.taken_at_original):
            errors.append(f"{file_name}: exif_taken_at_original mismatch")
        if not _datetimes_match(taken_record, record.taken_at_record):
            errors.append(f"{file_name}: exif_taken_at_record mismatch")

        if has_flood_classification:
            flood_class = col["flood_class"][index]
            score_flooded = col["flood_score_flooded"][index]
            score_non_flooded = col["flood_score_non_flooded"][index]

            if flood_class not in FLOOD_CLASS_VALUES:
                errors.append(f"{file_name}: invalid flood_class {flood_class!r}")

            for label, score in (
                ("flood_score_flooded", score_flooded),
                ("flood_score_non_flooded", score_non_flooded),
            ):
                if score is None or not (0.0 <= float(score) <= 1.0):
                    errors.append(f"{file_name}: {label} out of range: {score}")

            if score_flooded is not None and score_non_flooded is not None:
                expected_class = (
                    FLOOD_CLASS_FLOODED
                    if float(score_flooded) >= float(score_non_flooded)
                    else FLOOD_CLASS_NON_FLOODED
                )
                if flood_class != expected_class:
                    errors.append(f"{file_name}: flood_class does not match argmax scores")

        if has_flood_depth:
            vehicle_count = col["flood_depth_vehicle_count"][index]
            max_level = col["flood_depth_max_level"][index]
            high_danger = col["flood_depth_high_danger"][index]
            detections_raw = col["flood_depth_detections"][index]

            if vehicle_count is None or int(vehicle_count) < 0:
                errors.append(f"{file_name}: flood_depth_vehicle_count out of range")

            try:
                detections = parse_detections_json(detections_raw)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"{file_name}: invalid flood_depth_detections ({exc})")
                continue

            if int(vehicle_count) != len(detections):
                errors.append(
                    f"{file_name}: flood_depth_vehicle_count != detections length"
                )

            if len(detections) == 0:
                if max_level is not None:
                    errors.append(
                        f"{file_name}: flood_depth_max_level set without detections"
                    )
                if high_danger:
                    errors.append(
                        f"{file_name}: flood_depth_high_danger true without detections"
                    )
            else:
                computed_max = max(detection.level for detection in detections)
                if max_level != computed_max:
                    errors.append(f"{file_name}: flood_depth_max_level mismatch")
                computed_high = any(
                    detection.level in HIGH_DANGER_LEVELS for detection in detections
                )
                if bool(high_danger) != computed_high:
                    errors.append(f"{file_name}: flood_depth_high_danger mismatch")

            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                if x1 < 0 or y1 < 0 or x2 > width or y2 > height or x2 <= x1 or y2 <= y1:
                    errors.append(f"{file_name}: bbox out of image bounds")

    ok = not errors
    return ok, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate data/exif_images dataset.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Validate only the first N parquet rows (smoke test)",
    )
    args = parser.parse_args(argv)

    ok, errors = validate(out_dir=args.out_dir, sample=args.sample)
    if ok:
        print(f"OK: {args.out_dir}")
        return 0

    print(f"FAILED: {len(errors)} issue(s)", file=sys.stderr)
    for message in errors[:50]:
        print(message, file=sys.stderr)
    if len(errors) > 50:
        print(f"... and {len(errors) - 50} more", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
