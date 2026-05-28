#!/usr/bin/env python3
"""Rebuild index.parquet from existing images/ and source zip metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.exif import read_exif_from_bytes
from exif_images.metadata import load_posts_by_filename, post_text_fields
from exif_images.paths import images_dir

DEFAULT_IN = ROOT / "data" / "exif_images"
DEFAULT_ZIP = ROOT / "data" / "raw" / "social_media_2023-2024.zip"


def _base_schema() -> pa.Schema:
    return pa.schema(
        [
            ("file_name", pa.string()),
            ("platform", pa.string()),
            ("post_id", pa.string()),
            ("caption", pa.string()),
            ("tags", pa.string()),
            ("exif_taken_at_original", pa.timestamp("us", tz="UTC")),
            ("exif_taken_at_record", pa.timestamp("us", tz="UTC")),
            ("geometry", pa.string()),
        ]
    )


def rebuild(*, in_dir: Path, zip_path: Path, out_path: Path | None) -> int:
    manifest_path = in_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)

    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    images_subdir = manifest.get("images_subdir", "images")
    img_dir = images_dir(in_dir, subdir=images_subdir)
    posts_by_name = load_posts_by_filename(str(zip_path))

    rows: list[dict] = []
    for jpg_path in sorted(img_dir.glob("*.jpg")):
        record = read_exif_from_bytes(jpg_path.read_bytes())
        if record is None:
            raise ValueError(f"{jpg_path.name}: EXIF no longer qualifies")
        post_fields = post_text_fields(posts_by_name.get(jpg_path.name))
        rows.append(
            {
                "file_name": jpg_path.name,
                **post_fields,
                "exif_taken_at_original": record.taken_at_original,
                "exif_taken_at_record": record.taken_at_record,
                "geometry": record.geometry,
            }
        )

    target = out_path if out_path is not None else in_dir / "index.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_suffix(".parquet.staging")
    try:
        pq.write_table(pa.Table.from_pylist(rows, schema=_base_schema()), staging)
        staging.replace(target)
    finally:
        if staging.is_file() and not target.is_file():
            staging.replace(target)
        elif staging.is_file():
            staging.unlink()
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild index.parquet from images/.")
    parser.add_argument("--in-dir", type=Path, default=DEFAULT_IN)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output parquet path (default: <in-dir>/index.parquet)",
    )
    args = parser.parse_args(argv)

    try:
        count = rebuild(in_dir=args.in_dir, zip_path=args.zip, out_path=args.out)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out = args.out if args.out is not None else args.in_dir / "index.parquet"
    print(f"Wrote {count} rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
