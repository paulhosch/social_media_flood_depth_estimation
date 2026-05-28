# Social media data catalogue

Documentation for GIA social media exports and integration with the Hochwasser-Cockpit HTTP API.

- **[Raw downloads](docs/RAW_DATA.md)** — schema and per-file notes for everything under `data/raw/`
- **[HWC REST API](docs/HWC_REST_API.md)** — endpoints, post object schema, examples, and client notes (`GET /hw_posts`)
- **[ADR 0001](docs/adr/0001-canonical-hwc-flat-post.md)** — canonical `HwcPost` shape and build rules

## Build EXIF images dataset

From `data/raw/social_media_2023-2024.zip` (GPS + EXIF datetime filter, 2048 px re-encode):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_exif_images.py
.venv/bin/python scripts/enrich_flood_classification.py
.venv/bin/python scripts/fetch_flood_depth_model.py
.venv/bin/python scripts/enrich_flood_depth.py
.venv/bin/python scripts/validate_exif_images.py
```

Writes `data/exif_images/index.parquet` (17 columns after flood depth enrichment), `data/exif_images/images/*.jpg`, and `manifest.json`. See **[EXIF_IMAGES_DATASET.md](docs/EXIF_IMAGES_DATASET.md)** (full pipeline, schema, figures) and [RAW_DATA.md](docs/RAW_DATA.md#derived-dataset-dataexif_images).

| Layer | Model | Question |
|-------|-------|----------|
| Flood classification | [Flood-Image-Detection](https://huggingface.co/prithivMLmods/Flood-Image-Detection) | Is the scene flooded? |
| Flood depth | [FLOOD-DEPTH-ML](https://github.com/mayankmi/FLOOD-DEPTH-ML) `best_car.pt` | Vehicle inundation level (0–4) + boxes |

Depth labels are a visual proxy from detected vehicles, not hydraulic water depth.

## EXIF map viewer

One-page web app (Deck.gl + MapLibre) to browse geotagged images on a map with a time histogram and metadata side panel.

```bash
# After building and enriching the dataset (see above)
.venv/bin/python scripts/export_map_index.py

cd web/exif-map
npm install
npm run build
npm run preview
```

Open the URL shown by Vite preview (default `http://localhost:4173`). Images are served from `data/exif_images/images/` via `/dataset/images/` — keep that directory in place; do not copy JPEGs into `public/`.

Re-run enrichment scripts and `export_map_index.py` whenever you rebuild `data/exif_images/`. To refresh documentation figures: `.venv/bin/python scripts/generate_exif_dataset_doc_figures.py`.

## Publishing boundaries

Use this repository as the source of truth for code and docs only.

- **GitHub (private repository):** `scripts/`, `exif_images/`, `web/exif-map/`, docs, and reproducible build instructions.
- **Internal data storage:** full `data/exif_images/` outputs (`images/`, `index.parquet`, `manifest.json`) and raw archives.
- **Public app hosting:** static web build only, protected at the edge with Cloudflare Access.

The current `.gitignore` already excludes large raw archives, derived EXIF image outputs, and model weights from git history.

## Production map data endpoints

`web/exif-map` supports environment-based endpoints for hosted deployments:

- `VITE_MAP_INDEX_URL` (default: `/data/map-index.json`)
- `VITE_IMAGE_BASE_URL` (default: `/dataset/images`)

Local development keeps current behavior by default. For production, set both variables in the Cloudflare Pages project settings.

Export map index with profile selection:

```bash
# Internal full metadata (default)
.venv/bin/python scripts/export_map_index.py --profile internal-full

# Public-safe metadata (caption/tags/post_id redacted)
.venv/bin/python scripts/export_map_index.py --profile public-safe
```

## Cloudflare Pages + Access (minimal setup)

1. Push this repository to GitHub (`origin`).
2. In Cloudflare Pages, create a project from this GitHub repo:
   - **Root directory:** `web/exif-map`
   - **Build command:** `npm run build`
   - **Output directory:** `dist`
3. Set production environment variables:
   - `VITE_MAP_INDEX_URL` to your hosted `map-index.json` URL
   - `VITE_IMAGE_BASE_URL` to your protected image base URL
4. In Cloudflare Zero Trust, create an Access application for the Pages hostname.
5. Add policy: allow only internal emails (email OTP).

Validation checklist before sharing:

- Anonymous browser is blocked by Access.
- Authenticated users can load points and images.
- Internal raw/full data URLs are not publicly reachable.
- Rebuild flow works end to end: pipeline -> export -> deploy.

Detailed click-through setup is documented in [CLOUDFLARE_PAGES_ACCESS_DEPLOYMENT.md](docs/CLOUDFLARE_PAGES_ACCESS_DEPLOYMENT.md).
