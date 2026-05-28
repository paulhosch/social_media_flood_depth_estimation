"""Paths for the exif_images dataset layout."""

from __future__ import annotations

from pathlib import Path

IMAGES_SUBDIR = "images"


def images_dir(out_dir: Path, *, subdir: str = IMAGES_SUBDIR) -> Path:
    return out_dir / subdir


def image_path(out_dir: Path, file_name: str, *, subdir: str = IMAGES_SUBDIR) -> Path:
    return images_dir(out_dir, subdir=subdir) / file_name
