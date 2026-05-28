"""Flood scene classification via Hugging Face Flood-Image-Detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoImageProcessor, SiglipForImageClassification

if TYPE_CHECKING:
    from torch import Tensor

FLOOD_CLASSIFICATION_MODEL_ID = "prithivMLmods/Flood-Image-Detection"

FLOOD_CLASS_FLOODED = "flooded"
FLOOD_CLASS_NON_FLOODED = "non_flooded"

_MODEL_CLASS_INDEX_FLOODED = 0
_MODEL_CLASS_INDEX_NON_FLOODED = 1


@dataclass(frozen=True)
class FloodClassificationResult:
    flood_class: str
    flood_score_flooded: float
    flood_score_non_flooded: float


def flood_classification_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_flood_classification_model() -> tuple[
    SiglipForImageClassification,
    AutoImageProcessor,
    torch.device,
]:
    device = flood_classification_device()
    processor = AutoImageProcessor.from_pretrained(FLOOD_CLASSIFICATION_MODEL_ID)
    model = SiglipForImageClassification.from_pretrained(FLOOD_CLASSIFICATION_MODEL_ID)
    model.to(device)
    model.eval()
    return model, processor, device


def _result_from_probs(probs: list[float]) -> FloodClassificationResult:
    score_flooded = float(probs[_MODEL_CLASS_INDEX_FLOODED])
    score_non_flooded = float(probs[_MODEL_CLASS_INDEX_NON_FLOODED])
    if score_flooded >= score_non_flooded:
        flood_class = FLOOD_CLASS_FLOODED
    else:
        flood_class = FLOOD_CLASS_NON_FLOODED
    return FloodClassificationResult(
        flood_class=flood_class,
        flood_score_flooded=score_flooded,
        flood_score_non_flooded=score_non_flooded,
    )


def classify_flood_images_batch(
    images: list[Image.Image],
    *,
    model: SiglipForImageClassification,
    processor: AutoImageProcessor,
    device: torch.device,
    batch_size: int = 16,
) -> list[FloodClassificationResult]:
    """Run flood classification on a list of RGB PIL images."""
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    if not images:
        return []

    results: list[FloodClassificationResult] = []
    for start in range(0, len(images), batch_size):
        chunk = images[start : start + batch_size]
        rgb = [img.convert("RGB") for img in chunk]
        inputs = processor(images=rgb, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.no_grad():
            logits: Tensor = model(**inputs).logits
            probs = F.softmax(logits, dim=1)

        for row in probs.cpu().tolist():
            results.append(_result_from_probs(row))

    return results
