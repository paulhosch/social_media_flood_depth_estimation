"""Normalize GIA nested export posts to HWC flat posts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from catalogue.hwc_post import HWC_POST_KEYS, empty_hwc_post

_CLOCK_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T ](\d{2})[:-](\d{2})[:-](\d{2})(.*)$"
)


def post_richness_score(post: dict[str, Any]) -> int:
    """Higher score wins when deduplicating on (platform, post_id)."""
    score = 0
    geom = post.get("geom")
    if geom:
        score += 1000 + len(geom)
    if post.get("lat") is not None and post.get("lng") is not None:
        score += 100
    for field in ("city", "state", "zip", "street_name", "address"):
        if post.get(field):
            score += 10
    if post.get("image_url"):
        score += 50
    if post.get("caption"):
        score += 5
    return score


def _normalize_taken_at_string(value: str) -> str:
    """Fix GIA dash-separated clock fields for taken_at."""
    match = _CLOCK_RE.match(value.strip())
    if not match:
        return value.strip()
    date_part, hh, mm, ss, tail = match.groups()
    clock = f"{hh}:{mm}:{ss}"
    if "T" in value:
        return f"{date_part}T{clock}{tail}"
    return f"{date_part} {clock}{tail}"


def _parse_datetime(value: str) -> datetime | None:
    text = _normalize_taken_at_string(value)
    if len(text) >= 5 and text[-5] in "+-" and text[-3] != ":":
        try:
            fixed = text[:-5] + text[-5:-2] + ":" + text[-2:]
            return datetime.strptime(fixed, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            pass
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(text.replace("Z", "+0000"), fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def _to_timestamp_iso(value: str) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return value.strip()
    return parsed.isoformat()


def _tags_to_string(tags: Any) -> str:
    if tags is None:
        return ""
    if isinstance(tags, list):
        return json.dumps(tags, ensure_ascii=False)
    if isinstance(tags, str):
        return tags
    return str(tags)


def _geom_to_string(geom: Any) -> str | None:
    if geom is None:
        return None
    if isinstance(geom, str):
        return geom
    return json.dumps(geom, ensure_ascii=False, separators=(",", ":"))


def gia_post_to_hwc(raw: dict[str, Any]) -> dict[str, Any] | None:
    """
    Map one GIA nested post to an HWC flat post.

    Returns None when the row cannot be keyed (missing post_id).
    """
    if not raw:
        return None

    platform = raw.get("platform")
    post_id = raw.get("post_id")
    if not platform or not post_id:
        return None

    location = raw.get("location") or {}
    media = raw.get("media") or {}

    taken_raw = raw.get("posted_at") or media.get("taken_at")
    if taken_raw is None or taken_raw == "":
        taken_at = ""
        timestamp = ""
    else:
        taken_str = str(taken_raw)
        taken_at = _normalize_taken_at_string(taken_str)
        timestamp = _to_timestamp_iso(taken_str)

    post = empty_hwc_post()
    post.update(
        {
            "platform": str(platform),
            "post_id": str(post_id),
            "user_id": str(raw.get("user_id") or ""),
            "taken_at": taken_at,
            "timestamp": timestamp,
            "caption": str(raw.get("caption") or ""),
            "tags": _tags_to_string(raw.get("tags")),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "geom": _geom_to_string(location.get("geom")),
            "city": location.get("city"),
            "state": location.get("state"),
            "zip": location.get("zip"),
            "street_name": location.get("street_name"),
            "image_url": str(media.get("url") or ""),
            "image_filename": str(media.get("file_name") or ""),
            "image_width": int(media.get("width") or 0),
            "image_height": int(media.get("height") or 0),
        }
    )

    assert list(post.keys()) == list(HWC_POST_KEYS)
    return post
