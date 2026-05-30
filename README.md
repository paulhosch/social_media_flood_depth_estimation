# Social media data catalogue

Documentation and build pipelines for GIA social media exports, a geotagged EXIF image dataset with flood ML enrichments, and a map viewer.

**Python 3.13** · **License:** [MIT](LICENSE)

## Documentation

- **[EXIF images dataset](docs/EXIF_IMAGES_DATASET.md)** — build pipeline, schema, statistics, figures ([PDF](docs/EXIF_IMAGES_DATASET.pdf))
- **[Raw downloads](docs/RAW_DATA.md)** — GigaMove schema and per-file notes for `data/raw/`
- **[HWC REST API](docs/HWC_REST_API.md)** — flat post schema and `GET /hw_posts`
- **[CONTEXT.md](CONTEXT.md)** — terminology and HWC catalogue build overview
- **[Operational validation paper (PDF)](docs/OPERATIONAL_USAGE_SOCIAL_MEDIA_FLOOD_DEPTH_VALIDATION.pdf)** — background on EXIF-based flood validation at 1 m resolution

## Data access

Large artefacts are **not** in git. After cloning, obtain data separately:

| Artefact | Size (approx.) | How to get it |
|----------|----------------|---------------|
| **Viewer bundle** `exif-map-viewer-v1.0.0.zip` | ~550–650 MB | [GitHub Release v1.0.0](https://github.com/paulhosch/social_media_flood_depth_estimation/releases/tag/v1.0.0) — static map + all JPEGs + launchers (no Python/Node) |
| **EXIF dataset** `data/exif_images/` | ~520 MB | Institutional file share (same release or contact maintainer) — `images/`, `index.parquet`, `manifest.json` |
| **Raw GigaMove archives** | 1.9 MB – 53 GB | `./scripts/download_gigamove.sh` — see [RAW_DATA.md](docs/RAW_DATA.md) |

Verify downloads with the SHA256 checksum published on the GitHub Release page.

## View the map (no terminal)

1. Download and unzip `exif-map-viewer-v1.0.0.zip`.
2. Double-click the launcher for your OS (`Start EXIF Map.bat`, `Start EXIF Map.command`, or `start-exif-map.sh`).
3. Your browser opens `http://localhost:8080` with the full interactive map.

Supported platforms: Windows, macOS (Intel and Apple Silicon), Linux x86_64.

## Build EXIF images dataset

From `data/raw/social_media_2023-2024.zip` (GPS + EXIF datetime filter, within-post URL/content dedup, 2048 px re-encode):

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_exif_images.py
.venv/bin/python scripts/enrich_flood_classification.py
.venv/bin/python scripts/fetch_flood_depth_model.py
.venv/bin/python scripts/enrich_flood_depth.py
.venv/bin/python scripts/validate_exif_images.py
.venv/bin/python scripts/export_map_index.py
```

Build-time dedup is always on: within each `(platform, post_id)`, only one image per `media.url` (and one per identical file content) is kept. Bluesky carousel posts with distinct URLs are preserved.

**Legacy dataset without the source zip?** Deduplicate an existing `data/exif_images/` directory in place (preserves enrichment on canonical rows):

```bash
.venv/bin/python scripts/dedup_exif_images.py --dry-run   # preview
.venv/bin/python scripts/dedup_exif_images.py
.venv/bin/python scripts/validate_exif_images.py
.venv/bin/python scripts/export_map_index.py
```

Writes `data/exif_images/index.parquet` (15 columns after flood depth enrichment), `data/exif_images/images/*.jpg`, and `manifest.json`. See **[EXIF_IMAGES_DATASET.md](docs/EXIF_IMAGES_DATASET.md)** and [RAW_DATA.md](docs/RAW_DATA.md#derived-dataset-dataexif_images).

| Layer | Model | Question |
|-------|-------|----------|
| Flood classification | [Flood-Image-Detection](https://huggingface.co/prithivMLmods/Flood-Image-Detection) | Is the scene flooded? |
| Flood depth | [FLOOD-DEPTH-ML](https://github.com/mayankmi/FLOOD-DEPTH-ML) `best_car.pt` | Vehicle inundation level (0–4) + boxes |

Depth labels are a visual proxy from detected vehicles, not hydraulic water depth.

Regenerate documentation figures (optional):

```bash
.venv/bin/pip install -r requirements-docs.txt
.venv/bin/python scripts/generate_exif_dataset_doc_figures.py
```

## EXIF map viewer (development)

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

Re-run enrichment scripts and `export_map_index.py` whenever you rebuild `data/exif_images/` from the zip. After in-place dedup only, re-export the map index (enrichment re-run not required).

Export profiles:

```bash
.venv/bin/python scripts/export_map_index.py --profile internal-full   # default
.venv/bin/python scripts/export_map_index.py --profile public-safe      # redact caption/tags/post_id
```

Environment variables for custom endpoints (`web/exif-map/.env.example`):

- `VITE_MAP_INDEX_URL` (default: `/data/map-index.json`)
- `VITE_IMAGE_BASE_URL` (default: `/dataset/images`)

## HWC catalogue build

Normalize GIA nested JSON to flat `HwcPost` rows for Hochwasser-Cockpit API alignment:

```bash
./scripts/download_gigamove.sh   # if data/raw/ is empty
./scripts/build_catalogue.sh
```

Outputs: `data/canonical/catalogue.json`, `posts_api.json`, `manifest.json`. See [CONTEXT.md](CONTEXT.md).

## Publishing boundaries

- **GitHub (private):** code, docs, sample map index, reproducible build instructions.
- **Release / file share:** viewer bundle, full `data/exif_images/` outputs, raw archives.
- **Not in git:** JPEGs, Parquet, model weights, raw zips (see `.gitignore`).

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
pytest tests/ -q
```
