"""HWC REST flat post shape (25 keys). See docs/HWC_REST_API.md."""

SCHEMA_VERSION = "1.0"

HWC_POST_KEYS: tuple[str, ...] = (
    "platform",
    "post_id",
    "user_id",
    "taken_at",
    "timestamp",
    "caption",
    "tags",
    "lat",
    "lng",
    "geom",
    "city",
    "state",
    "zip",
    "address",
    "street_name",
    "location_id",
    "location_id_ref",
    "image_id",
    "image_id_ref",
    "main_id",
    "main_image_id",
    "image_url",
    "image_filename",
    "image_width",
    "image_height",
)


def empty_hwc_post() -> dict:
    """Return an HWC post with API-style empty sentinels."""
    return {
        "platform": "",
        "post_id": "",
        "user_id": "",
        "taken_at": "",
        "timestamp": "",
        "caption": "",
        "tags": "",
        "lat": None,
        "lng": None,
        "geom": None,
        "city": None,
        "state": None,
        "zip": None,
        "address": None,
        "street_name": None,
        "location_id": 0,
        "location_id_ref": 0,
        "image_id": None,
        "image_id_ref": 0,
        "main_id": None,
        "main_image_id": None,
        "image_url": "",
        "image_filename": "",
        "image_width": 0,
        "image_height": 0,
    }
