#!/usr/bin/env python3
"""Add flood depth columns to data/exif_images/index.parquet."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.exif import (
    INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION,
    INDEX_COLUMNS_WITH_FLOOD_DEPTH,
)
from exif_images.flood_depth import (
    FLOOD_DEPTH_MODEL_SOURCE,
    infer_flood_depth_image,
    load_flood_depth_model,
    result_summary_fields,
)
from exif_images.paths import image_path, images_dir

DEFAULT_IN = ROOT / "data" / "exif_images"
DEFAULT_MODEL = ROOT / "data" / "models" / "best_car.pt"


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
            ("flood_depth_max_level", pa.int8()),
            ("flood_depth_vehicle_count", pa.int32()),
            ("flood_depth_high_danger", pa.bool_()),
            ("flood_depth_detections", pa.string()),
        ]
    )


def enrich(
    *,
    in_dir: Path,
    model_path: Path,
    conf: float,
) -> dict:
    parquet_path = in_dir / "index.parquet"
    manifest_path = in_dir / "manifest.json"

    if not parquet_path.is_file():
        raise FileNotFoundError(parquet_path)
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("flood_classification") is None:
        raise ValueError(
            "manifest missing flood_classification; run enrich_flood_classification.py first"
        )

    images_subdir = manifest.get("images_subdir", "images")
    img_dir = images_dir(in_dir, subdir=images_subdir)
    if not img_dir.is_dir():
        raise FileNotFoundError(img_dir)

    table = pq.read_table(parquet_path)
    if table.column_names != list(INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION):
        raise ValueError(
            "index.parquet must have flood classification columns; "
            f"got {table.column_names}"
        )

    model = load_flood_depth_model(model_path)
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    file_names = table.column("file_name").to_pylist()
    base_columns = list(INDEX_COLUMNS_WITH_FLOOD_CLASSIFICATION)
    rows: list[dict] = []
    images_with_vehicles = 0
    images_high_danger = 0

    for index, name in enumerate(file_names):
        row = {col: table.column(col)[index].as_py() for col in base_columns}
        jpg_path = image_path(in_dir, name, subdir=images_subdir)
        if not jpg_path.is_file():
            raise FileNotFoundError(f"missing image for parquet row: {jpg_path}")

        result = infer_flood_depth_image(jpg_path, model=model, conf=conf)
        row.update(result_summary_fields(result))
        if result.vehicle_count > 0:
            images_with_vehicles += 1
        if result.high_danger:
            images_high_danger += 1
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

    manifest["index_columns"] = list(INDEX_COLUMNS_WITH_FLOOD_DEPTH)
    manifest["flood_depth"] = {
        "model_path": str(model_path.relative_to(ROOT))
        if model_path.is_relative_to(ROOT)
        else str(model_path),
        "model_source": FLOOD_DEPTH_MODEL_SOURCE,
        "conf_threshold": conf,
        "enriched_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "device": device,
        "row_count": len(rows),
        "images_with_vehicles": images_with_vehicles,
        "images_high_danger": images_high_danger,
    }

    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return manifest["flood_depth"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enrich index.parquet with flood depth detections."
    )
    parser.add_argument("--in-dir", type=Path, default=DEFAULT_IN)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--conf", type=float, default=0.5)
    args = parser.parse_args(argv)

    try:
        stats = enrich(in_dir=args.in_dir, model_path=args.model, conf=args.conf)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
