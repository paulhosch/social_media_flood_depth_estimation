# Hochwasser-Cockpit REST API

Reference for the live **Hochwasser-Cockpit (HWC)** HTTP API exposed at `hochwasser-cockpit.de`. This document covers **REST only** (endpoints, response shapes, field semantics, and client notes). It is derived from live probes on the deployment (May 2026) and team context (Jörn / Jan, branch `ca_refactored` on RWTH GitLab).

**Source of truth in production:** the running service. OpenAPI/Swagger on the host is currently broken (see [Discovery](#discovery-and-openapi)).

---

## Base URL

| Property | Value |
|----------|--------|
| Scheme | `https` |
| Host | `hochwasser-cockpit.de` |
| Port | `4334` |
| Base | `https://hochwasser-cockpit.de:4334` |

Example:

```text
https://hochwasser-cockpit.de:4334/hw_posts
```

---

## Authentication and access

| Observation | Notes |
|---------------|--------|
| `GET /hw_posts` | Works from project networks that can reach the host (e.g. RWTH/VPN). |
| Other clients | May receive `403 Forbidden` depending on IP or reverse-proxy rules. |
| Auth headers | Not documented in the live API; no `Authorization` requirement observed on successful `GET /hw_posts`. |
| TLS | Use `-k` only for local debugging if the certificate chain is incomplete; prefer proper CA trust in production. |

Confirm access policy with the cockpit operators before building automated crawlers.

---

## Endpoints (known)

| Method | Path | Status (probed) | Description |
|--------|------|-----------------|-------------|
| `GET` | `/hw_posts` | `200` (when allowed) | Full list of social-media posts as a JSON array. |
| `GET` | `/docs` | `500` | Intended API docs; returns internal server error. |
| `GET` | `/swagger` | `500` | Swagger UI (broken). |
| `GET` | `/swagger/index.html` | `500` | Swagger UI (broken). |
| `GET` | `/swagger/v1/swagger.json` | `500` | OpenAPI JSON (broken). |
| `GET` | `/api/swagger` | `500` | Alternate Swagger path (broken). |

No other public routes were confirmed in this project. Upload or single-resource routes (`/hw_posts/{id}`) may exist in the application code but were **not** verified on the live host.

---

## `GET /hw_posts`

Returns **all** posts in one response body (no pagination parameters were observed).

### Request

```http
GET /hw_posts HTTP/1.1
Host: hochwasser-cockpit.de:4334
Accept: application/json
```

**Query parameters:** none observed.

**Request body:** none.

### Response

| Property | Value |
|----------|--------|
| Status | `200 OK` (when accessible) |
| Content-Type | JSON (array) |
| Body shape | Top-level **JSON array** of post objects |
| Approximate size | ~**136 141** elements (May 2026 probe via `jq length`) |

There is no wrapper object (`{ "data": [...] }`); the payload **is** the array.

### Ordering

- Index `0` is **not** representative of the full dataset (often a seeded/demo Bluesky row).
- Do not infer global statistics from `.[0]` or `.[0:1000]` alone.

### Example (minimal `curl`)

```bash
curl -sk "https://hochwasser-cockpit.de:4334/hw_posts" | jq 'length'
curl -sk "https://hochwasser-cockpit.de:4334/hw_posts" | jq '.[0] | keys'
```

---

## Post object schema

Each array element is a **flat** object with **25** keys (fixed key set; no optional extension fields observed on the live API).

### Field reference

| Field | JSON type | Nullable | Description |
|-------|-----------|----------|-------------|
| `platform` | string | no | Source network, e.g. `flickr`, `bluesky`. |
| `post_id` | string | no | Platform-specific post identifier. |
| `user_id` | string | no | Platform user identifier. |
| `taken_at` | string | no | Capture/post time; **format varies** (see [Time fields](#time-fields)). |
| `timestamp` | string | no | Normalized timestamp, often ISO 8601 with offset. |
| `caption` | string | no | Post text (may be empty in edge cases). |
| `tags` | string | no | Tags as a **single string**; encoding varies (see [Tags](#tags)). |
| `lat` | number | yes | WGS84 latitude (degrees). |
| `lng` | number | yes | WGS84 longitude (degrees). |
| `geom` | string | yes | GeoJSON geometry serialized as a **JSON string** (not a nested object). |
| `city` | string | yes | Locality / place label. |
| `state` | string | yes | Region or state name. |
| `zip` | string | yes | Postal code. |
| `address` | string | yes | Street address line. |
| `street_name` | string | yes | Street name when split from address. |
| `location_id` | number | no | Internal location entity id (see [Sentinel values](#sentinel-values)). |
| `location_id_ref` | number | no | Reference to location row (often equals `location_id`). |
| `image_id` | number | yes | Internal image entity id. |
| `image_id_ref` | number | no | Reference to image row. |
| `main_id` | number | yes | Primary internal post id when set. |
| `main_image_id` | string | yes | Main image reference; may be string `"0"` on some rows. |
| `image_url` | string | no | HTTP(S) URL to image content (CDN or external site). |
| `image_filename` | string | no | File basename for the image. |
| `image_width` | number | no | Image width in pixels. |
| `image_height` | number | no | Image height in pixels. |

### Logical groupings

```text
Identity:     platform, post_id, user_id, main_id
Time:         taken_at, timestamp
Text:         caption, tags
Coordinates:  lat, lng, geom
Address:      city, state, zip, address, street_name, location_id, location_id_ref
Media:        image_id, image_id_ref, main_image_id, image_url, image_filename, image_width, image_height
```

### Natural key

For deduplication and joins between clients, use:

```text
(platform, post_id)
```

`main_id` is often `null` on sampled rows; do not rely on it as the only primary key unless the backend team confirms otherwise.

---

## Time fields

| Field | Example values | Notes |
|-------|----------------|-------|
| `taken_at` | `"2025-05-19 22:21:05"` | Space-separated local-style datetime. |
| `taken_at` | `"2024-09-18T13:15:36+0000"` | ISO-like with numeric offset (Flickr-style). |
| `timestamp` | `"2025-05-19T22:21:05+02:00"` | ISO 8601 with timezone offset. |

Clients should parse both fields with a tolerant datetime parser and treat `timestamp` as the preferred normalized instant when present.

---

## Tags

`tags` is always a **string**, but content varies by platform or export:

| Style | Example |
|-------|---------|
| Hashtag list | `"#hw-cockpit,#leverkusen,#prefa,#hochwasserschutz,#schutz"` |
| JSON array string | `"[\"feuerwehr\", \"hochwasser\", \"1692024\"]"` |

**Client rule:** if the value starts with `[`, parse as JSON array; otherwise split on commas/hashtags as needed.

---

## Geometry (`geom`)

When present, `geom` is a **string** containing escaped GeoJSON, not a JSON object.

Example (Flickr row):

```json
"geom": "{\"type\": \"Point\", \"coordinates\": [14.2591254, 51.6103701]}"
```

**Client rule:**

1. If `lat` and `lng` are set, use them for point maps.
2. Else if `geom` is non-null, `JSON.parse(geom)` (or `jq fromjson`) and read coordinates (GeoJSON order: `[longitude, latitude]` for `Point`).
3. Rows may have `geom` with **null** `lat`/`lng` (coordinates only in `geom`).

Supported geometry types in samples: **`Point`** (others may exist in the full dataset).

---

## Sentinel values

The API uses inconsistent “empty” markers for foreign-key-style fields:

| Value | Seen on | Likely meaning |
|-------|---------|----------------|
| `0` | `location_id`, `location_id_ref`, `image_id_ref` | No linked location/image entity |
| `null` | `image_id`, `main_id`, `geom`, address fields | Missing optional data |
| `"0"` | `main_image_id` (string) | Missing main image reference |

Treat `0` and `"0"` as **empty** unless the cockpit schema documentation states otherwise.

---

## Example records

### Bluesky (demo-style head row)

Often appears at array index `0`: marketing caption, `#hw-cockpit` tags, `gis-consult.de` image URL.

```json
{
  "platform": "bluesky",
  "post_id": "6502028834888439449_39421735004",
  "taken_at": "2025-05-19 22:21:05",
  "timestamp": "2025-05-19T22:21:05+02:00",
  "tags": "#hw-cockpit,#leverkusen,#prefa,#hochwasserschutz,#schutz",
  "caption": "…",
  "user_id": "39421735004",
  "location_id": 584,
  "location_id_ref": 584,
  "state": "North Rhine-Westphalia",
  "address": "Feldstraße 60a",
  "city": "Leverkusen, Germany",
  "zip": "51373",
  "lng": 6.939605236053467,
  "lat": 50.9571418762207,
  "image_id": 1,
  "image_id_ref": 1,
  "image_url": "https://www.gis-consult.de/wp-content/uploads/2023/10",
  "image_filename": "Support2-1024x683.jpg",
  "image_width": 1080,
  "image_height": 1350,
  "main_id": null,
  "street_name": null,
  "geom": null,
  "main_image_id": null
}
```

### Flickr (real CDN URL + GeoJSON point)

```json
{
  "platform": "flickr",
  "post_id": "54004293824",
  "taken_at": "2024-09-18T13:15:36+0000",
  "timestamp": "2024-09-18T15:15:36+02:00",
  "tags": "[\"feuerwehr\", \"feuerwehrbadgastein\", \"ffpongau\", \"hochwasser\", \"nieder\\u00f6sterreich\", \"1692024\"]",
  "caption": "Hochwasser Niederösterreich16.-17.9.2024",
  "user_id": "170716165@N05",
  "location_id": 0,
  "location_id_ref": 0,
  "state": null,
  "address": null,
  "city": null,
  "zip": null,
  "lng": null,
  "lat": null,
  "image_id": null,
  "image_id_ref": 0,
  "image_url": "https://live.staticflickr.com/65535/54004293824_87437721da_o.jpg",
  "image_filename": "7591442a-8cb4-4bff-9585-b5d36bf91695.jpg",
  "image_width": 1600,
  "image_height": 1200,
  "main_id": null,
  "street_name": null,
  "geom": "{\"type\": \"Point\", \"coordinates\": [14.2591254, 51.6103701]}",
  "main_image_id": "0"
}
```

---

## Discovery and OpenAPI

Probed paths (all returned **HTTP 500** with a generic internal error page):

- `/docs`
- `/swagger`
- `/swagger/index.html`
- `/swagger/v1/swagger.json`
- `/api/swagger`

Until these are fixed, treat **`GET /hw_posts`** as the authoritative contract and validate behaviour against live JSON.

Suggested discovery when access is available:

```bash
curl -skI "https://hochwasser-cockpit.de:4334/hw_posts"
curl -sk -X OPTIONS "https://hochwasser-cockpit.de:4334/hw_posts" -D -
```

---

## Analysis recipes (`jq`)

Record count and platforms:

```bash
curl -sk "https://hochwasser-cockpit.de:4334/hw_posts" | jq '{
  count: length,
  by_platform: (group_by(.platform) | map({platform: .[0].platform, n: length}) | sort_by(-.n))
}'
```

Coordinate coverage:

```bash
curl -sk "https://hochwasser-cockpit.de:4334/hw_posts" | jq '{
  total: length,
  lat_lng: [.[] | select(.lat != null and .lng != null)] | length,
  geom: [.[] | select(.geom != null and .geom != "")] | length
}'
```

First Flickr row with geometry:

```bash
curl -sk "https://hochwasser-cockpit.de:4334/hw_posts" \
  | jq '[.[] | select(.platform == "flickr" and .geom != null)][0]'
```

Parse `geom` on one row:

```bash
curl -sk "https://hochwasser-cockpit.de:4334/hw_posts" \
  | jq '[.[] | select(.geom != null)][0] | .geom | fromjson'
```

---

## Implementation notes for clients

1. **Payload size:** ~136k objects in one array — plan for memory, streaming, or periodic snapshots; do not assume pagination.
2. **Idempotency:** Use `(platform, post_id)` for upserts.
3. **Images:** Fetch via `image_url`; respect CDN rate limits and broken URLs.
4. **Geo:** Prefer explicit `lat`/`lng`; fall back to parsed `geom`; do not assume both are populated.
5. **Demo content:** Filter rows with `#hw-cockpit` or non-social `image_url` hosts if you need production-only analytics.
6. **Future upload API:** Team indicated data upload will be integrated into the workflow; not exposed on the probed host yet — coordinate with operators before implementing writes.

---

## Gaps and follow-ups

| Topic | Status |
|-------|--------|
| OpenAPI / Swagger | Not available (500 on all probed doc URLs). |
| `POST` / `PUT` upload | Mentioned in project communication; not verified on live host. |
| Single-post `GET` by id | Not verified. |
| Pagination (`limit`, `offset`, cursor) | Not observed on `GET /hw_posts`. |
| Rate limits | Not documented. |
| Canonical DB schema | Lives in RWTH GitLab `dcc/current-projects/hochwasser-cockpit/ca` (`ca_refactored`); requires institutional login. |

Update this file when the operators publish a fixed Swagger URL or additional routes.

---

## Document metadata

| Item | Value |
|------|--------|
| API base | `https://hochwasser-cockpit.de:4334` |
| Documented endpoint | `GET /hw_posts` |
| Last validated | 2026-05 (live `curl` + `jq` on bolzano) |
| Maintainer | social_media_data_catalogue project |
