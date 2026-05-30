"""Tests for within-post image deduplication."""

from __future__ import annotations

import unittest

from exif_images.dedup import PostImageDeduper


class PostImageDeduperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.deduper = PostImageDeduper()
        self.image_a = b"jpeg-bytes-a"
        self.image_b = b"jpeg-bytes-b"

    def test_same_url_within_post_is_duplicate(self) -> None:
        url = "https://example.com/a.jpg"
        self.assertIsNone(
            self.deduper.is_duplicate("flickr", "123", url, self.image_a)
        )
        self.assertEqual(
            self.deduper.is_duplicate("flickr", "123", url, self.image_b),
            "url",
        )

    def test_different_urls_within_post_are_kept(self) -> None:
        self.assertIsNone(
            self.deduper.is_duplicate(
                "bluesky",
                "post-1",
                "https://example.com/a.jpg",
                self.image_a,
            )
        )
        self.assertIsNone(
            self.deduper.is_duplicate(
                "bluesky",
                "post-1",
                "https://example.com/b.jpg",
                self.image_b,
            )
        )

    def test_same_bytes_different_urls_within_post_is_content_duplicate(self) -> None:
        self.assertIsNone(
            self.deduper.is_duplicate(
                "flickr",
                "123",
                "https://example.com/a.jpg",
                self.image_a,
            )
        )
        self.assertEqual(
            self.deduper.is_duplicate(
                "flickr",
                "123",
                "https://example.com/b.jpg",
                self.image_a,
            ),
            "content",
        )

    def test_same_bytes_across_posts_are_kept(self) -> None:
        self.assertIsNone(
            self.deduper.is_duplicate(
                "flickr",
                "123",
                "https://example.com/a.jpg",
                self.image_a,
            )
        )
        self.assertIsNone(
            self.deduper.is_duplicate(
                "flickr",
                "456",
                "https://example.com/a.jpg",
                self.image_a,
            )
        )

    def test_empty_url_uses_content_hash_only(self) -> None:
        self.assertIsNone(
            self.deduper.is_duplicate("flickr", "123", "", self.image_a)
        )
        self.assertEqual(
            self.deduper.is_duplicate("flickr", "123", "", self.image_a),
            "content",
        )


if __name__ == "__main__":
    unittest.main()
