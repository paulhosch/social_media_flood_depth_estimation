#!/usr/bin/env python3
"""Build canonical catalogue JSON from GIA raw exports."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from catalogue.hwc_post import SCHEMA_VERSION
from catalogue.normalize import gia_post_to_hwc, post_richness_score

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CANONICAL = ROOT / "data" / "canonical"

SOURCE_PATHS: tuple[str, ...] = (
    "posts_only/posts_2024-2025.json",
    "posts_only/posts_2026.json",
    "legacy_flickr.json",
)

QUARANTINED: tuple[str, ...] = ("posts_only/posts_2023-2024.json",)


def _load_posts(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    posts = payload.get("posts")
    if not isinstance(posts, list):
        raise ValueError(f"{path}: expected object with 'posts' array")
    return [row for row in posts if row]


def _dedupe(posts: list[dict]) -> tuple[list[dict], int]:
    best: dict[tuple[str, str], dict] = {}
    dropped = 0
    for post in posts:
        key = (post["platform"], post["post_id"])
        current = best.get(key)
        if current is None:
            best[key] = post
            continue
        dropped += 1
        if post_richness_score(post) > post_richness_score(current):
            best[key] = post
    return list(best.values()), dropped


def build(*, raw_dir: Path = RAW, out_dir: Path = CANONICAL) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    converted: list[dict] = []
    sources_loaded: list[str] = []
    skipped_no_id = 0

    for rel_path in SOURCE_PATHS:
        path = raw_dir / rel_path
        if not path.is_file():
            continue
        sources_loaded.append(rel_path)
        for raw in _load_posts(path):
            hwc = gia_post_to_hwc(raw)
            if hwc is None:
                skipped_no_id += 1
                continue
            converted.append(hwc)

    posts, dedupe_dropped = _dedupe(converted)
    posts.sort(key=lambda row: (row["platform"], row["post_id"]))

    catalogue = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "source": "gigamove",
        "posts": posts,
    }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "sources_loaded": sources_loaded,
        "quarantined": list(QUARANTINED),
        "post_count": len(posts),
        "rows_skipped_no_post_id": skipped_no_id,
        "dedupe_rows_dropped": dedupe_dropped,
    }

    with (out_dir / "catalogue.json").open("w", encoding="utf-8") as handle:
        json.dump(catalogue, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    with (out_dir / "posts_api.json").open("w", encoding="utf-8") as handle:
        json.dump(posts, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    with (out_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build HWC canonical catalogue from GIA raw JSON."
    )
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--out-dir", type=Path, default=CANONICAL)
    args = parser.parse_args(argv)

    manifest = build(raw_dir=args.raw_dir, out_dir=args.out_dir)
    print(json.dumps(manifest, indent=2))
    if not manifest["sources_loaded"]:
        print("warning: no raw source files found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
