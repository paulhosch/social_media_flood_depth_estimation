# Raw social media downloads (`data/raw`)

Schema reference for GIA / RWTH GigaMove exports stored under `data/raw`. Inspected May 2026.

These files use a **nested GIA export model** (objects `location` and `media`). That differs from the **flat** post shape returned by the live Hochwasser-Cockpit REST API — see [HWC_REST_API.md](HWC_REST_API.md).

---

## Inventory

Raw JSON and archives are **not** committed to git (except this documentation). Download locally with `scripts/download_gigamove.sh` or extract from GigaMove archives.

| Path | Size (approx.) | Description |
|------|----------------|-------------|
| `posts_only.zip` | 1.9 MB | Archive of the three `posts_only/*.json` files |
| `posts_only/posts_2023-2024.json` | 2.9 MB | Posts ~2023–2024, no images |
| `posts_only/posts_2024-2025.json` | 9.9 MB | Posts ~2024–2025, no images |
| `posts_only/posts_2026.json` | 674 KB | Posts 2026, no images |
| `legacy_flickr.json` | 2.6 GB | Flickr subset with OSM-derived `location.geom` |
| `social_media_2023-2024.zip` | 53 GB | Image files + embedded `workspace/posts.json` |

Re-download: `scripts/download_gigamove.sh`

---

## Shared JSON schema (all `*.json` post files)

### Root

```json
{
  "posts": [ /* post objects */ ]
}
```

| Property | Type | Description |
|----------|------|-------------|
| `posts` | array | List of post objects; may contain `null` elements (see per-file notes). |

### Post object (top level)

Every non-null post uses the same eight keys:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | yes | Source network: `flickr` or `bluesky`. |
| `post_id` | string \| null | varies | Platform post identifier. **Missing in `posts_2023-2024.json`.** |
| `posted_at` | string \| null | varies | Post time; format not normalized (see [Time](#posted_at)). |
| `user_id` | string | yes | Platform user identifier. |
| `caption` | string | yes | Post text; often empty string `""`. |
| `tags` | array of strings | yes | Hashtags/keywords as JSON array (not a single comma-separated string). |
| `location` | object \| null | yes | Place / geometry; see [Location](#location-object). |
| `media` | object \| null | yes | Image metadata; see [Media](#media-object). |

**Natural key (when present):** `(platform, post_id)`.

**Polygons:** Stored as GeoJSON under `location.geom` (object), not as a top-level `geom` field. Derived from caption/tags via OSM (street features), not water levels.

---

### `location` object

`null` when no place data is attached.

| Field | Type | Description |
|-------|------|-------------|
| `country` | string | Country name. |
| `state` | string | Region / state. |
| `city` | string | Locality. |
| `zip` | string | Postal code. |
| `street_name` | string | Street name. |
| `lat` | number | WGS84 latitude (degrees). |
| `lng` | number | WGS84 longitude (degrees). |
| `alt` | number | Altitude. |
| `geom` | object | GeoJSON geometry (see below). |

When `geom` is present it is a **parsed JSON object** (GeoJSON), e.g.:

```json
{
  "type": "Polygon",
  "coordinates": [[[16.2014817, 48.267816], [16.2017046, 48.2674349], ...]]
}
```

Observed `geom.type` values in `legacy_flickr.json`:

| Type | Count (of posts with `location.geom`) |
|------|--------------------------------------|
| `Polygon` | 4,974 |
| `Point` | 707 |
| `LineString` | 973 |
| `MultiLineString` | 365 |
| `MultiPolygon` | 95 |

Address fields (`lat`, `lng`, `city`, …) and `geom` can appear together or independently.

---

### `media` object

`null` when no image metadata is included (entire `posts_2023-2024.json` export).

| Field | Type | Description |
|-------|------|-------------|
| `type` | string \| null | Usually `"image"`; may be `null` in `legacy_flickr.json`. |
| `taken_at` | string \| null | Image capture time (ISO-like when set). |
| `url` | string | HTTP(S) URL to the image on the platform CDN. |
| `file_name` | string | UUID-based filename (e.g. `64c86c7a-425e-41ef-a6f5-6f91b18411c7.jpg`). |
| `width` | number | Image width in pixels. |
| `height` | number | Image height in pixels. |

Local files in `social_media_2023-2024.zip` live under `workspace/<file_name>`. GIA noted that scraped images do not always align 1:1 with post rows.

---

### `posted_at`

Formats vary by file:

| Pattern | Example | Seen in |
|---------|---------|---------|
| Space-separated date, dashes in time | `2024-09-18 16-04-05` | `posts_2024-2025.json`, `legacy_flickr.json` |
| ISO 8601 with `T` | `2026-04-01T19:08:41` | `posts_2026.json` |
| Missing | `null` | All rows in `posts_2023-2024.json` |

Use a tolerant parser; do not assume one format across exports.

---

### `tags`

Always a JSON **array of strings** in these downloads, e.g.:

```json
["hochwasser", "donau", "wien"]
```

---

## Per-file documentation

### `posts_only.zip`

| Property | Value |
|----------|--------|
| Contents | `posts_only/posts_2023-2024.json`, `posts_only/posts_2024-2025.json`, `posts_only/posts_2026.json` |
| Role | Convenience bundle for the “last 3 years, no images” GigaMove link |

Extract with:

```bash
unzip -d data/raw data/raw/posts_only.zip
```

---

### `posts_only/posts_2023-2024.json`

| Property | Value |
|----------|--------|
| Posts | 6,492 rows (6,491 non-null, 1 `null`) |
| Platforms | Flickr 2,771; Bluesky 3,720 |
| `post_id` | **All `null`** — cannot deduplicate or join on ID |
| `posted_at` | **All `null`** |
| `media` | **All `null`** |
| `location` | `null` on 5,846 rows; object on 645 (address + lat/lng, **no `geom`**) |
| Caption non-empty | ~5,721 |
| Tags non-empty | ~4,773 |

**Example (Flickr, incomplete row):**

```json
{
  "platform": "flickr",
  "post_id": null,
  "posted_at": null,
  "tags": ["oberwinter", "rhein", "hochwasser"],
  "caption": "",
  "user_id": "128753322@N08",
  "location": null,
  "media": null
}
```

**Caveat:** Treat as a separate/incomplete export until GIA backfills `post_id` and timestamps.

---

### `posts_only/posts_2024-2025.json`

| Property | Value |
|----------|--------|
| Posts | 14,928 (all non-null) |
| Platforms | Flickr 10,000; Bluesky 4,928 |
| Unique `(platform, post_id)` | 5,679 (heavy **in-file duplicates**: 9,249 duplicate `post_id`s) |
| `location.geom` | **0** (1,731 rows have address lat/lng only) |
| `media` | Object on every row |

**Example:**

```json
{
  "platform": "flickr",
  "post_id": "54006270683",
  "posted_at": "2024-09-18 16-04-05",
  "tags": ["flooddisaster", "hochwasser", "donau", "..."],
  "caption": "At the junction of the Donaukanal...",
  "user_id": "145003604@N02",
  "location": null,
  "media": {
    "type": "image",
    "taken_at": null,
    "url": "https://live.staticflickr.com/65535/54006270683_c0f0d34e47_o.jpg",
    "file_name": "64c86c7a-425e-41ef-a6f5-6f91b18411c7.jpg",
    "width": 5731,
    "height": 3812
  }
}
```

**Overlap:** 3,096 `post_id`s also appear in `legacy_flickr.json` (same text; legacy adds polygons and may use a different `media.file_name` UUID).

---

### `posts_only/posts_2026.json`

| Property | Value |
|----------|--------|
| Posts | 926 |
| Platforms | Flickr 90; Bluesky 836 |
| Unique `(platform, post_id)` | 811 (115 in-file duplicates) |
| `location.geom` | **0** (12 rows with address lat/lng) |
| `posted_at` | ISO `T` format on all rows |
| `media` | Object on every row |

Smallest recent slice; no overlap with `legacy_flickr.json` on `post_id`.

---

### `legacy_flickr.json`

| Property | Value |
|----------|--------|
| Posts | 10,000 (Flickr only) |
| Unique `post_id` | 3,096 (6,904 in-file duplicates) |
| `location.geom` | **7,114** posts |
| `location` object | 7,750 rows (geom with or without address fields) |
| `media` | Object on every row; `media.type` is `null` on all inspected rows |

**Example (polygon only in `location`):**

```json
{
  "platform": "flickr",
  "post_id": "54006270683",
  "posted_at": "2024-09-18 16-04-05",
  "tags": ["flooddisaster", "hochwasser", "..."],
  "caption": "At the junction of the Donaukanal...",
  "user_id": "145003604@N02",
  "location": {
    "geom": {
      "type": "Polygon",
      "coordinates": [[[16.2014817, 48.267816], ...]]
    }
  },
  "media": {
    "type": null,
    "taken_at": null,
    "url": "https://live.staticflickr.com/65535/54006270683_c0f0d34e47_o.jpg",
    "file_name": "05073677-14b3-4360-ad0f-86ce825b3a9b.jpg",
    "width": 5731,
    "height": 3812
  }
}
```

**Role:** Flickr rows aligned with `posts_2024-2025.json`, enriched with OSM street polygons in `location.geom`.

---

### `social_media_2023-2024.zip`

| Property | Value |
|----------|--------|
| Size | ~53 GB |
| Entries | 14,930 (14,928 JPEGs + 1 JSON + directory) |
| Layout | `workspace/<uuid>.jpg`, `workspace/posts.json` |

#### `workspace/posts.json`

| Property | Value |
|----------|--------|
| Uncompressed size | ~10.4 MB |
| Schema | Same `{ "posts": [...] }` as `posts_only/posts_2024-2025.json` |
| Post count | 14,928 |

Content matches the 2024–2025 JSON export (same `post_id`s and fields); bundled for offline image download.

#### `workspace/*.jpg`

| Property | Value |
|----------|--------|
| Count | 14,928 |
| Naming | UUID + `.jpg`, corresponds to `media.file_name` when linked |
| Join | Use `media.file_name` ↔ `workspace/<file_name>` after unzip |

**Disk note:** Extracting doubles storage (~53 GB archive + ~53 GB files). Ensure sufficient free space before `unzip`.

---

## Derived dataset: `data/exif_images/`

Portable subset built from `social_media_2023-2024.zip` (streamed; no full unzip required).

| Output | Description |
|--------|-------------|
| `images/*.jpg` | Re-encoded images (max 2048 px longest edge); `file_name` in Parquet is basename only |
| `index.parquet` | 8 columns after build; 11 after flood classification; 15 after flood depth (adds `flood_depth_max_level`, `flood_depth_vehicle_count`, `flood_depth_high_danger`, `flood_depth_detections`) |
| `manifest.json` | Build counts, `images_subdir`, processing parameters; `flood_classification` and `flood_depth` blocks after enrichment |
| `data/models/best_car.pt` | YOLO weights for flood depth (fetch with `scripts/fetch_flood_depth_model.py`; not committed) |

**Inclusion:** parseable EXIF GPS point and at least one of DateTimeOriginal or DateTime.

**Flood classification:** post-build step using [prithivMLmods/Flood-Image-Detection](https://huggingface.co/prithivMLmods/Flood-Image-Detection) on re-encoded JPEGs. Scores are heuristic model outputs for exploration, not ground-truth labels. If the home disk is full, set `HF_HOME` to a directory on a volume with free space (for example `export HF_HOME=/tmp/hf_cache`) before running `enrich_flood_classification.py`.

**Flood depth:** runs after flood classification on the same JPEGs using [FLOOD-DEPTH-ML](https://github.com/mayankmi/FLOOD-DEPTH-ML) YOLO weights. Per image it stores max vehicle inundation level (0–4), detection counts, a high-danger flag (any Level 3 or 4), and a JSON array of bounding boxes. These are visual proxies from vehicles in frame, not measured water depth.

```bash
pip install -r requirements.txt
python3 scripts/build_exif_images.py
python3 scripts/enrich_flood_classification.py
python3 scripts/fetch_flood_depth_model.py
python3 scripts/enrich_flood_depth.py
python3 scripts/validate_exif_images.py
python3 scripts/export_map_index.py
```

If `index.parquet` is missing but `images/` is intact, rebuild the base index with `python3 scripts/rebuild_index_parquet.py` before enrichment.

---

## Cross-file relationships

```text
posts_2023-2024.json     ── no post_id ──►  (no ID join to other files)

posts_2024-2025.json   ◄──── 3,096 shared post_id ────►  legacy_flickr.json
        │                                                      (+ location.geom)
        │
        └── same JSON as workspace/posts.json inside social_media_2023-2024.zip
                    └── workspace/*.jpg (by media.file_name)

posts_2026.json        ── no post_id overlap with legacy ──►
```

| Join key | Reliable? |
|----------|-----------|
| `(platform, post_id)` | Yes, except `posts_2023-2024.json` |
| `media.file_name` | Yes, between JSON and extracted `workspace/` images |
| `media.url` | Yes, for CDN fetch / verification |
| Caption + tags + `user_id` | Fallback only for 2023–2024 rows |

---

## Mapping to HWC REST (flat) schema

For upload or comparison with `GET /hw_posts`, map nested fields roughly as follows:

| GIA raw (`data/raw`) | HWC REST ([HWC_REST_API.md](HWC_REST_API.md)) |
|----------------------|-----------------------------------------------|
| `posted_at` / `media.taken_at` | `taken_at`, `timestamp` (normalize timezone) |
| `tags` (array) | `tags` (string: comma-separated or JSON-string) |
| `caption` | `caption` |
| `location.lat`, `location.lng` | `lat`, `lng` |
| `location.geom` (object) | `geom` (JSON **string**, escaped) |
| `location.city`, `state`, `zip`, `street_name` | same flat names |
| `media.url` | `image_url` |
| `media.file_name` | `image_filename` |
| `media.width`, `media.height` | `image_width`, `image_height` |
| — | `location_id`, `image_id`, `main_id`, … (internal IDs; often `0` / `null` on API) |

---

## Data quality notes

1. **Deduplicate** before curation: `posts_2024-2025.json` and `legacy_flickr.json` contain many repeated `post_id`s. The EXIF build (`scripts/build_exif_images.py`) deduplicates within each `(platform, post_id)` by `media.url` and raw-byte SHA256 — see [EXIF_IMAGES_DATASET.md](EXIF_IMAGES_DATASET.md#manifestjson).
2. **`posts_2023-2024.json`** is missing identifiers and media; keep separate until updated by GIA.
3. **Polygons** exist only in `legacy_flickr.json` (`location.geom`); other JSON files have no polygons as of this download.
4. **Images** in the large zip are not guaranteed 1:1 with post metadata (per GIA email); prefer `media.url` for verification.
5. **Instagram URLs** may expire; Flickr links were still valid when shared (May 2026).

---

## Related documentation

- [HWC_REST_API.md](HWC_REST_API.md) — production flat post schema on `hochwasser-cockpit.de:4334`
- [README.md](../README.md) — project overview
