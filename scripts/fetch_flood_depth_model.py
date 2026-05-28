#!/usr/bin/env python3
"""Download FLOOD-DEPTH-ML YOLO weights to data/models/best_car.pt."""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "models" / "best_car.pt"

MODEL_URL = (
    "https://github.com/mayankmi/FLOOD-DEPTH-ML/raw/main/best_car.pt"
)
MODEL_SOURCE = "https://github.com/mayankmi/FLOOD-DEPTH-ML"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(*, out_path: Path, force: bool) -> dict:
    if out_path.is_file() and not force:
        return {
            "path": str(out_path),
            "bytes": out_path.stat().st_size,
            "sha256": _sha256(out_path),
            "skipped": True,
            "model_source": MODEL_SOURCE,
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=120) as response:
            data = response.read()
        tmp_path.write_bytes(data)
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.is_file():
            tmp_path.unlink()
        raise

    return {
        "path": str(out_path),
        "bytes": out_path.stat().st_size,
        "sha256": _sha256(out_path),
        "skipped": False,
        "model_source": MODEL_SOURCE,
        "url": MODEL_URL,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download best_car.pt for flood depth enrichment."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the file already exists",
    )
    args = parser.parse_args(argv)

    try:
        stats = fetch(out_path=args.out, force=args.force)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    import json

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
