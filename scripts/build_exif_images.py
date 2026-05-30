#!/usr/bin/env python3
"""Build the portable exif_images dataset from social_media_2023-2024.zip."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.dedup import PostImageDeduper
from exif_images.exif import INDEX_COLUMNS, classify_jpeg_bytes, read_exif_from_bytes
from exif_images.metadata import load_posts_by_filename, media_url, post_text_fields
from exif_images.paths import IMAGES_SUBDIR, image_path, images_dir
from exif_images.resize import prepare_output_jpeg

DEFAULT_ZIP = ROOT / "data" / "raw" / "social_media_2023-2024.zip"
DEFAULT_OUT = ROOT / "data" / "exif_images"


def _clear_output_dir(out_dir: Path) -> None:
    img_dir = images_dir(out_dir)
    if img_dir.is_dir():
        shutil.rmtree(img_dir)
    for name in ("index.parquet", "manifest.json"):
        path = out_dir / name
        if path.is_file():
            path.unlink()
    # Legacy flat layout: remove jpgs at dataset root.
    for path in out_dir.glob("*.jpg"):
        path.unlink()


def _output_dir_has_artifacts(out_dir: Path) -> bool:
    if (out_dir / "index.parquet").exists() or (out_dir / "manifest.json").exists():
        return True
    if any(images_dir(out_dir).glob("*.jpg")):
        return True
    return any(out_dir.glob("*.jpg"))


def _row_from_record(
    file_name: str,
    record,
    post_fields: dict[str, str],
) -> dict:
    return {
        "file_name": file_name,
        **post_fields,
        "exif_taken_at_original": record.taken_at_original,
        "exif_taken_at_record": record.taken_at_record,
        "geometry": record.geometry,
    }


def build(
    *,
    zip_path: Path,
    out_dir: Path,
    max_dimension: int,
    jpeg_quality: int,
    overwrite: bool,
) -> dict:
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    if _output_dir_has_artifacts(out_dir):
        if not overwrite:
            raise FileExistsError(
                f"{out_dir} already contains dataset files; pass --overwrite to replace"
            )
        _clear_output_dir(out_dir)

    posts_by_name = load_posts_by_filename(str(zip_path))
    images_dir(out_dir).mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    deduper = PostImageDeduper()
    stats = {
        "zip_jpg_total": 0,
        "included_count": 0,
        "skipped_gps_stub": 0,
        "skipped_no_gps_or_datetime": 0,
        "skipped_corrupt": 0,
        "skipped_duplicate_url": 0,
        "skipped_duplicate_content": 0,
        "unmatched_post_metadata": 0,
    }

    with zipfile.ZipFile(zip_path) as zf:
        jpg_members = sorted(
            name
            for name in zf.namelist()
            if name.startswith("workspace/") and name.lower().endswith(".jpg")
        )
        stats["zip_jpg_total"] = len(jpg_members)

        for member in jpg_members:
            file_name = Path(member).name
            try:
                data = zf.read(member)
            except Exception:
                stats["skipped_corrupt"] += 1
                continue

            record = read_exif_from_bytes(data)
            if record is None:
                kind = classify_jpeg_bytes(data)
                if kind == "corrupt":
                    stats["skipped_corrupt"] += 1
                elif kind == "gps_stub":
                    stats["skipped_gps_stub"] += 1
                else:
                    stats["skipped_no_gps_or_datetime"] += 1
                continue

            post = posts_by_name.get(file_name)
            if post is None:
                stats["unmatched_post_metadata"] += 1
            post_fields = post_text_fields(post)

            skip_reason = deduper.is_duplicate(
                post_fields["platform"],
                post_fields["post_id"] or file_name,
                media_url(post),
                data,
            )
            if skip_reason is not None:
                stats[f"skipped_duplicate_{skip_reason}"] += 1
                continue

            output_bytes = prepare_output_jpeg(
                data,
                record,
                max_dimension=max_dimension,
                jpeg_quality=jpeg_quality,
            )
            image_path(out_dir, file_name).write_bytes(output_bytes)

            rows.append(_row_from_record(file_name, record, post_fields))
            stats["included_count"] += 1

    table = pa.Table.from_pylist(
        rows,
        schema=pa.schema(
            [
                ("file_name", pa.string()),
                ("platform", pa.string()),
                ("post_id", pa.string()),
                ("caption", pa.string()),
                ("tags", pa.string()),
                (
                    "exif_taken_at_original",
                    pa.timestamp("us", tz="UTC"),
                ),
                (
                    "exif_taken_at_record",
                    pa.timestamp("us", tz="UTC"),
                ),
                ("geometry", pa.string()),
            ]
        ),
    )
    pq.write_table(table, out_dir / "index.parquet")

    manifest = {
        "dataset": "exif_images",
        "images_subdir": IMAGES_SUBDIR,
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_zip": str(zip_path.relative_to(ROOT))
        if zip_path.is_relative_to(ROOT)
        else str(zip_path),
        "filter": {
            "gps": "parseable_exif_point_geojson",
            "datetime": "require_at_least_one_of_DateTimeOriginal_or_DateTime",
        },
        "image_processing": {
            "max_dimension_px": max_dimension,
            "jpeg_quality": jpeg_quality,
            "always_reencode": True,
        },
        "dedup": {
            "scope": "within (platform, post_id)",
            "methods": ["media.url", "sha256_raw_bytes"],
            "skipped_duplicate_url": stats["skipped_duplicate_url"],
            "skipped_duplicate_content": stats["skipped_duplicate_content"],
        },
        "index_columns": list(INDEX_COLUMNS),
        "posts_json_rows": len(posts_by_name),
        **stats,
    }

    with (out_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build data/exif_images dataset.")
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-dimension", type=int, default=2048)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    try:
        manifest = build(
            zip_path=args.zip,
            out_dir=args.out_dir,
            max_dimension=args.max_dimension,
            jpeg_quality=args.jpeg_quality,
            overwrite=args.overwrite,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
