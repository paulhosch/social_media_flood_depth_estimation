"""Within-post image deduplication for the EXIF build pipeline."""

from __future__ import annotations

import hashlib
from typing import Literal

SkipReason = Literal["url", "content"]


class PostImageDeduper:
    """Track included images per post by media URL and raw-byte SHA256."""

    def __init__(self) -> None:
        self._seen_urls: dict[tuple[str, str], set[str]] = {}
        self._seen_hashes: dict[tuple[str, str], set[str]] = {}

    def is_duplicate(
        self,
        platform: str,
        post_id: str,
        media_url: str | None,
        raw_bytes: bytes,
    ) -> SkipReason | None:
        """Return skip reason or None if the image should be kept (and register it)."""
        key = (platform, post_id)
        url = (media_url or "").strip()
        content_hash = hashlib.sha256(raw_bytes).hexdigest()

        if url:
            seen_urls = self._seen_urls.setdefault(key, set())
            if url in seen_urls:
                return "url"

        seen_hashes = self._seen_hashes.setdefault(key, set())
        if content_hash in seen_hashes:
            return "content"

        if url:
            self._seen_urls.setdefault(key, set()).add(url)
        seen_hashes.add(content_hash)
        return None
