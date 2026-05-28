"""Vehicle inundation depth inference via FLOOD-DEPTH-ML YOLO weights."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2

if TYPE_CHECKING:
    from ultralytics import YOLO

FLOOD_DEPTH_MODEL_FILENAME = "best_car.pt"
FLOOD_DEPTH_MODEL_SOURCE = "https://github.com/mayankmi/FLOOD-DEPTH-ML"

HIGH_DANGER_LEVELS = frozenset({3, 4})
VALID_LEVELS = frozenset(range(5))


@dataclass(frozen=True)
class FloodDepthDetection:
    level: int
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass(frozen=True)
class FloodDepthResult:
    max_level: int | None
    vehicle_count: int
    level_counts: dict[int, int]
    high_danger: bool
    detections: list[FloodDepthDetection]


def load_flood_depth_model(model_path: Path) -> YOLO:
    from ultralytics import YOLO

    if not model_path.is_file():
        raise FileNotFoundError(model_path)
    return YOLO(str(model_path))


def _empty_level_counts() -> dict[int, int]:
    return {level: 0 for level in range(5)}


def infer_flood_depth_image(
    path: Path,
    *,
    model: YOLO,
    conf: float,
) -> FloodDepthResult:
    frame = cv2.imread(str(path))
    if frame is None:
        raise ValueError(f"cannot read image: {path}")

    results = model(frame, conf=conf, verbose=False)
    detections: list[FloodDepthDetection] = []
    level_counts = _empty_level_counts()

    for box in results[0].boxes:
        cls = int(box.cls[0])
        if cls not in VALID_LEVELS:
            continue
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].cpu().numpy())
        detections.append(
            FloodDepthDetection(
                level=cls,
                confidence=confidence,
                bbox=(x1, y1, x2, y2),
            )
        )
        level_counts[cls] += 1

    vehicle_count = len(detections)
    if vehicle_count == 0:
        return FloodDepthResult(
            max_level=None,
            vehicle_count=0,
            level_counts=level_counts,
            high_danger=False,
            detections=[],
        )

    max_level = max(detection.level for detection in detections)
    high_danger = any(detection.level in HIGH_DANGER_LEVELS for detection in detections)
    return FloodDepthResult(
        max_level=max_level,
        vehicle_count=vehicle_count,
        level_counts=level_counts,
        high_danger=high_danger,
        detections=detections,
    )


def detection_to_dict(detection: FloodDepthDetection) -> dict[str, Any]:
    return {
        "level": detection.level,
        "confidence": detection.confidence,
        "bbox": list(detection.bbox),
    }


def detections_to_json(detections: list[FloodDepthDetection]) -> str:
    payload = [detection_to_dict(detection) for detection in detections]
    return json.dumps(payload, separators=(",", ":"))


def parse_detections_json(raw: str) -> list[FloodDepthDetection]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("flood_depth_detections must be a JSON array")

    detections: list[FloodDepthDetection] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("each detection must be an object")
        level = int(item["level"])
        confidence = float(item["confidence"])
        bbox_raw = item["bbox"]
        if not isinstance(bbox_raw, list) or len(bbox_raw) != 4:
            raise ValueError("bbox must be [x1, y1, x2, y2]")
        bbox = tuple(int(v) for v in bbox_raw)
        if level not in VALID_LEVELS:
            raise ValueError(f"invalid level {level}")
        detections.append(
            FloodDepthDetection(level=level, confidence=confidence, bbox=bbox)
        )
    return detections


def result_summary_fields(result: FloodDepthResult) -> dict[str, Any]:
    return {
        "flood_depth_max_level": result.max_level,
        "flood_depth_vehicle_count": result.vehicle_count,
        "flood_depth_high_danger": result.high_danger,
        "flood_depth_detections": detections_to_json(result.detections),
    }
