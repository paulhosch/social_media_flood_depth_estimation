#!/usr/bin/env python3
"""Generate figures for docs/EXIF_IMAGES_DATASET.md."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import seaborn as sns
from matplotlib.lines import Line2D
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exif_images.detection_overlay import draw_detections_on_axes
from exif_images.exif import geometry_coordinates
from exif_images.flood_classification import (
    FLOOD_CLASS_FLOODED,
    FLOOD_CLASS_NON_FLOODED,
)
from exif_images.flood_depth import FloodDepthDetection, parse_detections_json
from exif_images.paths import image_path

DATASET_DIR = ROOT / "data" / "exif_images"
FIGURES_DIR = ROOT / "docs" / "exif_images" / "figures"
STATS_JSON = FIGURES_DIR / "dataset_stats.json"

GRID_ROWS = 3
GRID_COLS = 3
GRID_SIZE = GRID_ROWS * GRID_COLS

COLOR_NON_FLOODED = "#2ca02c"
COLOR_FLOODED = "#1f77b4"


def _load_frame() -> tuple[pd.DataFrame, dict]:
    manifest_path = DATASET_DIR / "manifest.json"
    parquet_path = DATASET_DIR / "index.parquet"
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    table = pq.read_table(parquet_path)
    rows: list[dict] = []
    for i in range(table.num_rows):
        geometry = table.column("geometry")[i].as_py()
        lon, lat = geometry_coordinates(geometry)
        original = table.column("exif_taken_at_original")[i].as_py()
        record = table.column("exif_taken_at_record")[i].as_py()
        taken = original if original is not None else record
        if taken is not None and hasattr(taken, "to_pydatetime"):
            taken = taken.to_pydatetime()

        detections = parse_detections_json(
            table.column("flood_depth_detections")[i].as_py()
        )
        detection_levels = {detection.level for detection in detections}
        max_level = (
            max(detection_levels) if detection_levels else None
        )

        rows.append(
            {
                "file_name": table.column("file_name")[i].as_py(),
                "flood_class": table.column("flood_class")[i].as_py(),
                "flood_score_flooded": float(
                    table.column("flood_score_flooded")[i].as_py()
                ),
                "flood_score_non_flooded": float(
                    table.column("flood_score_non_flooded")[i].as_py()
                ),
                "flood_depth_vehicle_count": int(
                    table.column("flood_depth_vehicle_count")[i].as_py()
                ),
                "flood_depth_max_level": max_level,
                "detections": detections,
                "detection_levels": detection_levels,
                "lon": lon,
                "lat": lat,
                "taken_at": taken,
            }
        )
    return pd.DataFrame(rows), manifest


def _dataset_stats(df: pd.DataFrame, manifest: dict) -> dict:
    flooded = df["flood_class"] == FLOOD_CLASS_FLOODED
    has_vehicle = df["flood_depth_vehicle_count"] > 0
    return {
        "zip_jpg_total": manifest["zip_jpg_total"],
        "included_gps_datetime": manifest["included_count"],
        "flooded": int(flooded.sum()),
        "non_flooded": int((~flooded).sum()),
        "flooded_with_vehicles": int((flooded & has_vehicle).sum()),
        "any_with_vehicles": int(has_vehicle.sum()),
        "examples_level_0": int((df["flood_depth_max_level"] == 0).sum()),
        "examples_level_1_2": int(df["flood_depth_max_level"].isin([1, 2]).sum()),
        "examples_level_3_4": int(
            df["detection_levels"].map(lambda levels: bool(levels & {3, 4})).sum()
        ),
        "manifest_built_at": manifest.get("built_at"),
        "flood_classification_model": manifest.get("flood_classification", {}).get(
            "model_id"
        ),
        "flood_depth_model_source": manifest.get("flood_depth", {}).get(
            "model_source"
        ),
    }


def _select_examples(
    df: pd.DataFrame,
    mask: pd.Series,
    *,
    sort_by: str,
    ascending: bool = False,
    n: int = GRID_SIZE,
) -> pd.DataFrame:
    subset = df.loc[mask].sort_values(sort_by, ascending=ascending)
    if subset.empty:
        return subset
    if len(subset) <= n:
        return subset
    positions = np.linspace(0, len(subset) - 1, n, dtype=int)
    return subset.iloc[positions]


def _plot_cell(
    ax: plt.Axes,
    row: pd.Series,
    *,
    annotate_detections: bool,
    subtitle: str | None = None,
) -> None:
    path = image_path(DATASET_DIR, row["file_name"])
    with Image.open(path) as pil_image:
        ax.imshow(pil_image)
    ax.set_xticks([])
    ax.set_yticks([])

    detections: list[FloodDepthDetection] = row["detections"]
    if annotate_detections and detections:
        draw_detections_on_axes(ax, detections)

    title_parts = [row["file_name"][:8] + "…"]
    if subtitle:
        title_parts.append(subtitle)
    elif detections:
        title_parts.append(f"max L{row['flood_depth_max_level']}")
    ax.set_title("\n".join(title_parts), fontsize=8)


def figure_example_grid(
    df: pd.DataFrame,
    *,
    title: str,
    selection: pd.DataFrame,
    out_path: Path,
    annotate_detections: bool,
    empty_note: str | None = None,
) -> None:
    fig, axes = plt.subplots(GRID_ROWS, GRID_COLS, figsize=(14, 14))
    fig.suptitle(title, fontsize=14, y=0.995)

    for index, ax in enumerate(axes.flat):
        if index < len(selection):
            row = selection.iloc[index]
            score = row["flood_score_flooded"]
            if row["flood_class"] == FLOOD_CLASS_NON_FLOODED:
                score = row["flood_score_non_flooded"]
            subtitle = None
            if not annotate_detections:
                subtitle = f"{row['flood_class']} ({score:.2f})"
            elif row["flood_depth_max_level"] is not None:
                subtitle = f"max L{row['flood_depth_max_level']}"
            _plot_cell(
                ax,
                row,
                annotate_detections=annotate_detections,
                subtitle=subtitle,
            )
        else:
            ax.axis("off")
            if index == len(selection) and empty_note:
                ax.text(
                    0.5,
                    0.5,
                    empty_note,
                    ha="center",
                    va="center",
                    fontsize=10,
                    transform=ax.transAxes,
                )

    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def figure_example_grids(df: pd.DataFrame) -> None:
    flooded = _select_examples(
        df,
        df["flood_class"] == FLOOD_CLASS_FLOODED,
        sort_by="flood_score_flooded",
    )
    non_flooded = _select_examples(
        df,
        df["flood_class"] == FLOOD_CLASS_NON_FLOODED,
        sort_by="flood_score_non_flooded",
    )
    level_0 = _select_examples(
        df,
        df["flood_depth_max_level"] == 0,
        sort_by="flood_score_flooded",
    )
    level_1_2 = _select_examples(
        df,
        df["flood_depth_max_level"].isin([1, 2]),
        sort_by="flood_depth_max_level",
    )
    level_3_4_mask = df["detection_levels"].map(lambda levels: bool(levels & {3, 4}))
    level_3_4 = _select_examples(
        df,
        level_3_4_mask,
        sort_by="flood_depth_max_level",
        ascending=False,
    )

    figure_example_grid(
        df,
        title="Example images classified as flooded (Flood-Image-Detection)",
        selection=flooded,
        out_path=FIGURES_DIR / "fig09_examples_flooded.png",
        annotate_detections=False,
    )
    figure_example_grid(
        df,
        title="Example images classified as non-flooded (Flood-Image-Detection)",
        selection=non_flooded,
        out_path=FIGURES_DIR / "fig10_examples_non_flooded.png",
        annotate_detections=False,
    )
    figure_example_grid(
        df,
        title="Vehicle detections at inundation Level 0 (FLOOD-DEPTH-ML)",
        selection=level_0,
        out_path=FIGURES_DIR / "fig11_examples_level_0.png",
        annotate_detections=True,
    )
    figure_example_grid(
        df,
        title="Vehicle detections at inundation Levels 1–2 (FLOOD-DEPTH-ML)",
        selection=level_1_2,
        out_path=FIGURES_DIR / "fig12_examples_level_1_2.png",
        annotate_detections=True,
    )
    note = None
    if len(level_3_4) < GRID_SIZE:
        note = (
            f"Only {len(level_3_4)} image(s) in the dataset\n"
            "with Level 3 or 4 detections"
        )
    figure_example_grid(
        df,
        title="Vehicle detections at inundation Levels 3–4 (FLOOD-DEPTH-ML)",
        selection=level_3_4,
        out_path=FIGURES_DIR / "fig13_examples_level_3_4.png",
        annotate_detections=True,
        empty_note=note,
    )


def figure_counts(stats: dict, out_path: Path) -> None:
    labels = [
        "All images\nin source zip",
        "EXIF GPS +\ndatetime",
        "Flooded\n(classifier)",
        "Flooded +\nvehicle detected",
    ]
    values = [
        stats["zip_jpg_total"],
        stats["included_gps_datetime"],
        stats["flooded"],
        stats["flooded_with_vehicles"],
    ]
    colors = ["#bdbdbd", "#969696", COLOR_FLOODED, "#08519c"]

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor="#333333", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Image count")
    ax.set_title("Dataset funnel: source archive to flooded subset with vehicles")
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.01,
            f"{value:,}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def figure_map(df: pd.DataFrame, out_path: Path) -> None:
    import contextily as cx
    import geopandas as gpd
    from shapely.geometry import Point

    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326",
    )
    gdf = gdf.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(10, 8))

    for flood_flag, color in ((False, COLOR_NON_FLOODED), (True, COLOR_FLOODED)):
        for vehicle_flag, marker, size in ((False, "o", 22), (True, "s", 30)):
            mask = (gdf["flood_class"] == FLOOD_CLASS_FLOODED) == flood_flag
            mask &= (gdf["flood_depth_vehicle_count"] > 0) == vehicle_flag
            subset = gdf.loc[mask]
            if subset.empty:
                continue
            ax.scatter(
                subset.geometry.x,
                subset.geometry.y,
                c=color,
                marker=marker,
                s=size,
                alpha=0.75,
                edgecolors="white",
                linewidths=0.35,
                zorder=3,
            )

    cx.add_basemap(
        ax,
        source=cx.providers.CartoDB.Positron,
        zoom="auto",
        attribution_size=7,
    )

    ax.set_axis_off()
    ax.set_title("Geotagged images by flood class and vehicle detection")

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=COLOR_NON_FLOODED,
            markersize=8,
            label="Non-flooded",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=COLOR_FLOODED,
            markersize=8,
            label="Flooded",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#555555",
            markersize=8,
            label="No vehicle",
        ),
        Line2D(
            [0],
            [0],
            marker="s",
            color="w",
            markerfacecolor="#555555",
            markersize=8,
            label="Vehicle detected",
        ),
    ]
    ax.legend(handles=legend_handles, loc="lower left", framealpha=0.92)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def figure_timeline(df: pd.DataFrame, out_path: Path) -> None:
    taken = df["taken_at"].dropna()
    if taken.empty:
        raise ValueError("no taken_at timestamps for timeline figure")

    daily = (
        df.dropna(subset=["taken_at"])
        .assign(day=lambda d: pd.to_datetime(d["taken_at"]).dt.date)
        .groupby(["day", "flood_class"])
        .size()
        .unstack(fill_value=0)
    )
    for col in (FLOOD_CLASS_FLOODED, FLOOD_CLASS_NON_FLOODED):
        if col not in daily.columns:
            daily[col] = 0
    daily = daily.sort_index()
    days = [datetime.combine(d, datetime.min.time()) for d in daily.index]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(
        days,
        daily[FLOOD_CLASS_NON_FLOODED],
        label="Non-flooded",
        color=COLOR_NON_FLOODED,
        s=28,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.35,
    )
    ax.scatter(
        days,
        daily[FLOOD_CLASS_FLOODED],
        label="Flooded",
        color=COLOR_FLOODED,
        s=28,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.35,
    )

    ax.set_xlabel("Date (EXIF capture time, UTC)")
    ax.set_ylabel("Images per day")
    ax.set_title("Daily image counts by flood classification")
    ax.legend(loc="upper right")
    fig.autofmt_xdate(rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    sns.set_theme(style="whitegrid", context="notebook")
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df, manifest = _load_frame()
    stats = _dataset_stats(df, manifest)
    STATS_JSON.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    figure_counts(stats, FIGURES_DIR / "fig04_dataset_funnel.png")
    figure_map(df, FIGURES_DIR / "fig05_spatial_distribution.png")
    figure_timeline(df, FIGURES_DIR / "fig06_daily_timeline.png")
    figure_example_grids(df)

    print(json.dumps(stats, indent=2))
    print(f"Wrote figures to {FIGURES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
