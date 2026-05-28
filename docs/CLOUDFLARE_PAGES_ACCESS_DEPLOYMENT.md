# Cloudflare Pages + Access deployment

Minimal production setup for this project: private code and data workflows with a public app URL protected by Cloudflare Access.

## 1) GitHub repository

- Repository: `https://github.com/paulhosch/social_media_flood_depth_estimation.git`
- Keep repository visibility private.
- Keep large dataset artefacts outside git (`data/exif_images`, raw zips, model weights).

## 2) Build and publish map index

From repository root:

```bash
.venv/bin/python scripts/export_map_index.py --profile public-safe
```

Use `--profile internal-full` only for internal-only endpoints.

## 3) Cloudflare Pages project

In Cloudflare Pages:

- Connect GitHub repository.
- Framework preset: `Vite`.
- Root directory: `web/exif-map`
- Build command: `npm run build`
- Build output directory: `dist`

Set environment variables in Pages:

- `VITE_MAP_INDEX_URL`: hosted URL to `map-index.json`
- `VITE_IMAGE_BASE_URL`: protected image base URL

## 4) Cloudflare Access protection

In Cloudflare Zero Trust:

1. Create an Access application for the Pages hostname.
2. Add policy: Allow -> Emails ending in your internal domain (or explicit allowlist).
3. Authentication method: email one-time PIN (OTP).
4. Deny all users not matching the allow policy.

## 5) Validation checklist

- Anonymous browser access to the Pages URL is blocked.
- Allowed user receives OTP and can log in.
- Map points load from `VITE_MAP_INDEX_URL`.
- Image requests load from `VITE_IMAGE_BASE_URL` after auth.
- No direct public listing of internal dataset storage.
- Rebuild flow works: pipeline -> export map index -> push code -> Pages deploy.
