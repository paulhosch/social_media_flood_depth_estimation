"""Load minimal GIA post fields from the image zip."""

from __future__ import annotations

import json
import zipfile
from typing import Any


def load_posts_by_filename(zip_path: str | zipfile.ZipFile) -> dict[str, dict[str, Any]]:
    """Map media.file_name -> post object from workspace/posts.json."""
    if isinstance(zip_path, zipfile.ZipFile):
        zf = zip_path
        close = False
    else:
        zf = zipfile.ZipFile(zip_path)
        close = True

    try:
        payload = json.loads(zf.read("workspace/posts.json"))
    finally:
        if close:
            zf.close()

    posts = payload.get("posts")
    if not isinstance(posts, list):
        raise ValueError("workspace/posts.json: expected object with 'posts' array")

    by_name: dict[str, dict[str, Any]] = {}
    for post in posts:
        if not post:
            continue
        media = post.get("media") or {}
        file_name = media.get("file_name")
        if file_name:
            by_name[str(file_name)] = post
    return by_name


def media_url(post: dict[str, Any] | None) -> str:
    """Return media.url from a GIA post object, or empty string when missing."""
    if not post:
        return ""
    media = post.get("media") or {}
    return str(media.get("url") or "")


def post_text_fields(post: dict[str, Any] | None) -> dict[str, str]:
    """Return platform, post_id, caption, tags for index.parquet."""
    if not post:
        return {
            "platform": "",
            "post_id": "",
            "caption": "",
            "tags": "[]",
        }

    tags = post.get("tags")
    if isinstance(tags, list):
        tags_json = json.dumps(tags, ensure_ascii=False)
    elif tags is None:
        tags_json = "[]"
    else:
        tags_json = json.dumps(tags, ensure_ascii=False)

    return {
        "platform": str(post.get("platform") or ""),
        "post_id": str(post.get("post_id") or ""),
        "caption": str(post.get("caption") or ""),
        "tags": tags_json,
    }
