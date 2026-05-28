"""Draw FLOOD-DEPTH-ML boxes and labels (matches web/exif-map ImageWithDetections)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.patches as patches
from matplotlib.axes import Axes
if TYPE_CHECKING:
    from exif_images.flood_depth import FloodDepthDetection

# Same palette as web/exif-map/src/lib/floodDepth.ts (L0 green, L1–L2 yellow, L3–L4 red)
INUNDATION_LEVEL_HEX: dict[int, str] = {
    0: "#22c55e",
    1: "#eab308",
    2: "#eab308",
    3: "#ef4444",
    4: "#ef4444",
}


def inundation_level_hex(level: int) -> str:
    return INUNDATION_LEVEL_HEX.get(level, "#94a3b8")


def draw_detections_on_axes(
    ax: Axes,
    detections: list[FloodDepthDetection],
    *,
    line_width: float = 2.0,
) -> None:
    """Overlay bboxes and Level/confidence labels in image pixel coordinates."""
    if not detections:
        return

    xlim = ax.get_xlim()
    font_size = max(8.0, min(12.0, (xlim[1] if xlim[1] else 800) / 70.0))
    label_height_px = font_size + 4.0

    for detection in detections:
        x1, y1, x2, y2 = detection.bbox
        color = inundation_level_hex(detection.level)
        width = x2 - x1
        height = y2 - y1

        ax.add_patch(
            patches.Rectangle(
                (x1, y1),
                width,
                height,
                linewidth=line_width,
                edgecolor=color,
                facecolor="none",
            )
        )

        label = f"Level {detection.level}: {detection.confidence:.2f}"
        label_y = max(y1 - 4.0, label_height_px)
        label_x = x1

        ax.text(
            label_x + 4.0,
            label_y,
            label,
            color="white",
            fontsize=font_size,
            fontfamily="sans-serif",
            va="top",
            ha="left",
            bbox={
                "boxstyle": "square,pad=0.25",
                "facecolor": color,
                "edgecolor": color,
                "linewidth": 0,
            },
            clip_on=True,
        )
