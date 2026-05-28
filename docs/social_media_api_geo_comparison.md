# Social Media API: Geolocation & Datetime Data Comparison

*Last updated: May 2026*

Comparison of geolocation and temporal metadata available from major social media APIs, with emphasis on distinguishing **capture location/time** (where and when the image/video was actually taken) from **post location/time** (where and when it was published).

## Comparison Table

| Platform | API | Capture Location (where taken) | Post Location (where posted) | Capture Time (when taken) | Post Time (when published) |
|---|---|---|---|---|---|
| **Flickr** | Flickr API | ✅ Lat/lon via `geo.getLocation` (accuracy 1–16) + raw GPS EXIF via `getExif` | ⚠️ Same field (could be EXIF or manual tag, indistinguishable) | ✅ `date_taken` from EXIF `DateTimeOriginal`, with `datetakengranularity` (0–10) | ✅ `date_upload` (Unix timestamp, fully separate) |
| **Twitter/X** | X API v2 | ❌ EXIF stripped, no capture coords | 🟣 Degraded since June 2019: only `place` bounding boxes (city/venue), no precise GPS | ❌ No capture time field | ✅ `created_at` (ISO 8601, second precision) |
| **TikTok** | Research API | ❌ No location fields, no EXIF | 🟠 `region_code`: 2-letter country of *account registration*, not content origin | ❌ No capture time field | ✅ `create_time` (UTC Unix epoch, seconds) |
| **YouTube** | Data API v3 | 🟡 `recordingDetails.location` (lat/lon) exists but almost never populated post-2018; was always manually set | 🟡 Named place tag (post-2023 for Shorts/streams), not coords | 🟡 `recordingDetails.recordingDate` exists but manually set by creator, rarely populated | ✅ `snippet.publishedAt` (ISO 8601) |
| **Instagram** | Graph API | ❌ EXIF stripped; `location`/`latitude`/`longitude` fields deprecated Jan 2025 | 🟣 `location` (user-selected venue) deprecated Apr 2025 | ❌ No capture time field | ✅ `timestamp` (ISO 8601) |
| **Bluesky** | AT Protocol | ❌ Zero location fields in official lexicons | ❌ No location of any kind | ❌ No EXIF or capture time | ✅ `createdAt` (ISO 8601, but client-set, not server-validated) |
| **Snapchat** | Snap Map (unofficial) | ⚠️ Device GPS at capture time (via undocumented private API) | ⚠️ Same as capture (near-real-time posting) | ⚠️ Timestamp per snap (capture ≈ post time for ephemeral snaps) | ⚠️ Same as capture time |
| **Snapchat** | Official APIs (Snap Kit) | ❌ No content or location access | ❌ N/A | ❌ N/A | ❌ N/A |

**Legend:** ✅ Available and reliable, ⚠️ Partial / user-tagged / unofficial, 🟡 Exists but rarely populated, 🟠 Coarse (country-level), 🟣 Deprecated, ❌ Not available

## Key Findings

**Only Flickr explicitly separates capture time from post time.** It provides `date_taken` (from EXIF when available, with a granularity indicator) alongside `date_upload`. Every other platform provides only the publication timestamp.

**Only Flickr reliably provides capture-location coordinates via API.** The `flickr.photos.geo.getLocation` endpoint returns lat/lon with an accuracy level, and `flickr.photos.getExif` can return raw GPS EXIF tags. However, coordinates could also originate from manual user tagging, and there is no API flag to distinguish the two. Checking for the presence of GPS tags in raw EXIF is the best available heuristic.

**No platform guarantees verified capture location.** Even Flickr's geo data can be manually overridden. Snapchat's Snap Map comes closest (device GPS at capture, near-real-time posting), but has no official research API and content is ephemeral (typically 24h).

**All major platforms except Flickr strip EXIF metadata** (including GPS and timestamps) from publicly accessible images. Instagram, Twitter/X, TikTok, and Facebook ingest original EXIF on upload for internal use but remove it from the public-facing file.

**Twitter's 2019 removal of precise geotagging** (replaced by coarse place bounding boxes) and **Instagram's 2025 deprecation of all location fields** have severely degraded the landscape for geo-social research compared to 5–10 years ago.

## Platform Ranking for Geo-Research (e.g., flood mapping)

1. **Flickr**: Rich geo + temporal metadata, EXIF access, spatial search. User base skews toward photographers.
2. **Snapchat (Snap Map)**: Excellent real-time capture-point GPS, but no official API, ephemeral content, requires reverse-engineering.
3. **YouTube**: `recordingDetails` fields exist in principle but almost never populated on modern uploads.
4. **Twitter/X**: Only coarse place bounding boxes since 2019. No capture time. EXIF stripped.
5. **TikTok**: Country-level account registration only. No coordinates, no capture time.
6. **Instagram**: Zero geolocation data as of 2025. Fully deprecated.
7. **Bluesky**: No geolocation capability whatsoever.
