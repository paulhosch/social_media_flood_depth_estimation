#!/usr/bin/env python3
"""Add flood classification columns to data/exif_images/index.parquet."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.exif import INDEX_COLUMNS, INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION
from exif_images.flood_classification import (
    FLOOD_CLASSIFICATION_MODEL_ID,
    classify_flood_images_batch,
    load_flood_classification_model,
)
from exif_images.paths import image_path, images_dir

DEFAULT_IN = ROOT / "data" / "exif_images"


def _index_parquet_schema() -> pa.Schema:
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
            ("flood_class", pa.string()),
            ("flood_score_flooded", pa.float64()),
            ("flood_score_non_flooded", pa.float64()),
        ]
    )


def enrich(
    *,
    in_dir: Path,
    batch_size: int,
) -> dict:
    parquet_path = in_dir / "index.parquet"
    manifest_path = in_dir / "manifest.json"

    if not parquet_path.is_file():
        raise FileNotFoundError(parquet_path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    images_subdir = manifest.get("images_subdir", "images")
    img_dir = images_dir(in_dir, subdir=images_subdir)
    if not img_dir.is_dir():
        raise FileNotFoundError(img_dir)

    table = pq.read_table(parquet_path)
    base_columns = list(INDEX_COLUMNS)
    if table.column_names[: len(base_columns)] != base_columns:
        raise ValueError(
            f"index.parquet must start with {base_columns}; got {table.column_names}"
        )

    file_names = table.column("file_name").to_pylist()
    pil_images: list[Image.Image] = []
    for name in file_names:
        path = image_path(in_dir, name, subdir=images_subdir)
        if not path.is_file():
            raise FileNotFoundError(f"missing image for parquet row: {path}")
        pil_images.append(Image.open(path))

    model, processor, device = load_flood_classification_model()
    try:
        classification = classify_flood_images_batch(
            pil_images,
            model=model,
            processor=processor,
            device=device,
            batch_size=batch_size,
        )
    finally:
        for img in pil_images:
            img.close()

    rows: list[dict] = []
    for index, name in enumerate(file_names):
        row = {col: table.column(col)[index].as_py() for col in base_columns}
        result = classification[index]
        row["flood_class"] = result.flood_class
        row["flood_score_flooded"] = result.flood_score_flooded
        row["flood_score_non_flooded"] = result.flood_score_non_flooded
        rows.append(row)

    out_table = pa.Table.from_pylist(rows, schema=_index_parquet_schema())
    staging = parquet_path.with_suffix(".parquet.staging")
    try:
        pq.write_table(out_table, staging)
        staging.replace(parquet_path)
    finally:
        if staging.is_file() and not parquet_path.is_file():
            staging.replace(parquet_path)
        elif staging.is_file():
            staging.unlink()

    manifest["index_columns"] = list(INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION)
    manifest["flood_classification"] = {
        "model_id": FLOOD_CLASSIFICATION_MODEL_ID,
        "enriched_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "device": str(device),
        "batch_size": batch_size,
        "row_count": len(rows),
    }

    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return manifest["flood_classification"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enrich index.parquet with flood classification scores."
    )
    parser.add_argument("--in-dir", type=Path, default=DEFAULT_IN)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args(argv)

    try:
        stats = enrich(in_dir=args.in_dir, batch_size=args.batch_size)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
