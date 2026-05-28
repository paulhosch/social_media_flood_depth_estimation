# Social media data catalogue

Documentation and build pipeline for **GIA GigaMove exports** aligned with the **Hochwasser-Cockpit (HWC) REST API** flat post format.

## Language

**Hochwasser-Cockpit (HWC)**:
The RWTH flood-cockpit project that stores flood-related social posts and exposes them at `https://hochwasser-cockpit.de:4334` (not the cellular-automaton `ca` simulation repo).
_Avoid_: using “cockpit” alone without HWC when meaning the social API.

**HWC REST API**:
HTTP JSON interface to the production post store; canonical read path documented here is `GET /hw_posts`.
_Avoid_: assuming upload routes exist without verification.

**HwcPost**:
One social post as a **flat** object with exactly **25** keys matching [docs/HWC_REST_API.md](docs/HWC_REST_API.md). This is the canonical interchange shape.
_Avoid_: “post object” when the nested GIA export is meant.

**Catalogue envelope**:
Local JSON wrapper `{ schema_version, generated_at, source, posts: HwcPost[] }` used only in this repo—not returned by `GET /hw_posts`.
_Avoid_: sending the envelope to the live API.

**GIA raw export**:
Nested JSON under `data/raw/` (`location`, `media` objects). Ingest-only; never the canonical store.
_Avoid_: building features directly on nested fields.

**Quarantine**:
Raw files excluded from the canonical build until they have reliable keys (e.g. `posts_2023-2024.json` without `post_id`).
_Avoid_: “delete” or “ignore permanently”—quarantine means set aside, not discard.

**Natural key**:
`(platform, post_id)` for deduplication and joins between raw, catalogue, and API rows.

## Relationships

- **GIA raw exports** are transformed into **HwcPost** rows and written to a **catalogue envelope** under `data/canonical/`.
- **HWC REST API** defines the **HwcPost** field set; a literal API mirror is `posts_api.json` (top-level array, no wrapper).
- **`legacy_flickr.json`** enriches the same Flickr ids as `posts_2024-2025.json` with `location.geom` polygons; the build keeps the richer row on dedupe.
- **`social_media_2023-2024.zip`** bundles the same JSON as `posts_2024-2025` plus JPEGs; the build reads the extracted JSON files, not the zip.

## Flagged ambiguities

- **“Cockpit” on GitLab `ca` repo** is flood **simulation**, not the social-media API.
- **`tags` encoding** on the API is a single string (comma-list or JSON-array string); the build uses `json.dumps` on GIA arrays to match Flickr-style API rows.
- **`posts_2023-2024.json`** may be merged later when GIA backfills `post_id`; until then it stays quarantined.

## Build

```bash
./scripts/build_catalogue.sh
```

Outputs: `data/canonical/catalogue.json`, `posts_api.json`, `manifest.json`. See [docs/adr/0001-canonical-hwc-flat-post.md](docs/adr/0001-canonical-hwc-flat-post.md).
