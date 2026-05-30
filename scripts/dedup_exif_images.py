#!/usr/bin/env python3
"""Deduplicate an existing exif_images dataset in place (no source zip required)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.dedup import PostImageDeduper
from exif_images.exif import (
    INDEX_COLUMNS,
    INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION,
    INDEX_COLUMNS_WITH_FLOOD_DEPTH,
)
from exif_images.metadata import media_url
from exif_images.paths import IMAGES_SUBDIR, image_path, images_dir

DEFAULT_IN = ROOT / "data" / "exif_images"
DEFAULT_POSTS = ROOT / "data" / "raw" / "posts_only" / "posts_2024-2025.json"

ALLOWED_COLUMN_SETS = (
    INDEX_COLUMNS,
    INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION,
    INDEX_COLUMNS_WITH_FLOOD_DEPTH,
)


def _load_posts_by_filename(posts_json: Path) -> dict[str, dict]:
    with posts_json.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    posts = payload.get("posts")
    if not isinstance(posts, list):
        raise ValueError(f"{posts_json}: expected object with 'posts' array")

    by_name: dict[str, dict] = {}
    for post in posts:
        if not post:
            continue
        media = post.get("media") or {}
        file_name = media.get("file_name")
        if file_name:
            by_name[str(file_name)] = post
    return by_name


def _recompute_flood_depth_stats(rows: list[dict]) -> dict[str, int]:
    images_with_vehicles = 0
    images_high_danger = 0
    for row in rows:
        vehicle_count = row.get("flood_depth_vehicle_count")
        if vehicle_count is not None and int(vehicle_count) > 0:
            images_with_vehicles += 1
        if row.get("flood_depth_high_danger"):
            images_high_danger += 1
    return {
        "images_with_vehicles": images_with_vehicles,
        "images_high_danger": images_high_danger,
    }


def dedup(
    *,
    in_dir: Path,
    posts_json: Path,
    dry_run: bool,
) -> dict:
    parquet_path = in_dir / "index.parquet"
    manifest_path = in_dir / "manifest.json"

    if not parquet_path.is_file():
        raise FileNotFoundError(parquet_path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    if not posts_json.is_file():
        raise FileNotFoundError(posts_json)

    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    images_subdir = manifest.get("images_subdir", IMAGES_SUBDIR)
    table = pq.read_table(parquet_path)
    columns = tuple(table.column_names)
    if columns not in ALLOWED_COLUMN_SETS:
        raise ValueError(
            f"unexpected index.parquet columns {columns}; "
            f"expected one of {ALLOWED_COLUMN_SETS}"
        )

    posts_by_name = _load_posts_by_filename(posts_json)
    rows = table.to_pylist()
    rows.sort(key=lambda row: str(row["file_name"]))

    deduper = PostImageDeduper()
    keep_rows: list[dict] = []
    drop_names: list[str] = []
    stats = {
        "input_count": len(rows),
        "skipped_duplicate_url": 0,
        "skipped_duplicate_content": 0,
    }

    for row in rows:
        file_name = str(row["file_name"])
        platform = str(row.get("platform") or "")
        post_id = str(row.get("post_id") or "") or file_name
        jpg_path = image_path(in_dir, file_name, subdir=images_subdir)
        if not jpg_path.is_file():
            raise FileNotFoundError(f"missing image for parquet row: {jpg_path}")

        skip_reason = deduper.is_duplicate(
            platform,
            post_id,
            media_url(posts_by_name.get(file_name)),
            jpg_path.read_bytes(),
        )
        if skip_reason is not None:
            stats[f"skipped_duplicate_{skip_reason}"] += 1
            drop_names.append(file_name)
            continue
        keep_rows.append(row)

    stats["included_count"] = len(keep_rows)
    stats["removed_count"] = len(drop_names)

    if not dry_run:
        staging = parquet_path.with_suffix(".parquet.staging")
        try:
            pq.write_table(
                pa.Table.from_pylist(keep_rows, schema=table.schema),
                staging,
            )
            staging.replace(parquet_path)
        finally:
            if staging.is_file() and not parquet_path.is_file():
                staging.replace(parquet_path)
            elif staging.is_file():
                staging.unlink()

        for file_name in drop_names:
            jpg_path = image_path(in_dir, file_name, subdir=images_subdir)
            if jpg_path.is_file():
                jpg_path.unlink()

    manifest["included_count"] = stats["included_count"]
    manifest["dedup"] = {
        "scope": "within (platform, post_id)",
        "methods": ["media.url", "sha256_on_disk_jpeg_bytes"],
        "applied_in_place_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "posts_json": str(posts_json.relative_to(ROOT))
        if posts_json.is_relative_to(ROOT)
        else str(posts_json),
        **stats,
    }

    if manifest.get("flood_classification") is not None:
        manifest["flood_classification"]["row_count"] = stats["included_count"]

    if manifest.get("flood_depth") is not None:
        if columns != INDEX_COLUMNS_WITH_FLOOD_DEPTH:
            raise ValueError(
                "manifest records flood_depth but index.parquet is missing depth columns"
            )
        depth_stats = _recompute_flood_depth_stats(keep_rows)
        manifest["flood_depth"]["row_count"] = stats["included_count"]
        manifest["flood_depth"].update(depth_stats)

    if not dry_run:
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    return {
        "dry_run": dry_run,
        **stats,
        "dropped_file_names": drop_names,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Remove within-post duplicate images from an existing exif_images "
            "dataset, preserving enrichment columns on canonical rows."
        )
    )
    parser.add_argument("--in-dir", type=Path, default=DEFAULT_IN)
    parser.add_argument(
        "--posts-json",
        type=Path,
        default=DEFAULT_POSTS,
        help="GIA posts JSON for media.url join (default: posts_2024-2025.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report duplicates without writing parquet, deleting JPEGs, or updating manifest",
    )
    args = parser.parse_args(argv)

    try:
        result = dedup(
            in_dir=args.in_dir,
            posts_json=args.posts_json,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary = {key: value for key, value in result.items() if key != "dropped_file_names"}
    print(json.dumps(summary, indent=2))
    if args.dry_run and result["removed_count"]:
        print(
            f"\nWould remove {result['removed_count']} JPEG(s); "
            "re-run without --dry-run to apply.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
