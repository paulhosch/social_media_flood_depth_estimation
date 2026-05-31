#!/usr/bin/env bash
# Build a self-contained EXIF map viewer zip (static site + JPEGs + miniserve + launchers).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

VERSION="v1.0.0"
MINISERVE_TAG="v0.35.0"
PORT=8080
PROFILE="internal-full"
SKIP_DOWNLOAD=0
SKIP_NPM=0
PYTHON="${ROOT}/.venv/bin/python"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Build release/exif-map-viewer-\${VERSION}/ and exif-map-viewer-\${VERSION}.zip.

Options:
  --version TAG       Bundle version tag (default: ${VERSION})
  --profile NAME      map-index export profile (default: ${PROFILE})
  --port N            HTTP port for launchers (default: ${PORT})
  --skip-download     Reuse bin/ miniserve binaries if present
  --skip-npm          Skip npm run build (reuse web/exif-map/dist)
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="$2"
      shift 2
      ;;
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --skip-download)
      SKIP_DOWNLOAD=1
      shift
      ;;
    --skip-npm)
      SKIP_NPM=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

BUNDLE_NAME="exif-map-viewer-${VERSION}"
STAGING="${ROOT}/release/${BUNDLE_NAME}"
IMAGES_SRC="${ROOT}/data/exif_images/images"
WEB_DIR="${ROOT}/web/exif-map"
DIST_DIR="${WEB_DIR}/dist"
ZIP_PATH="${ROOT}/release/${BUNDLE_NAME}.zip"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    exit 1
  fi
}

download_miniserve() {
  local asset="$1"
  local dest="$2"
  local url="https://github.com/svenstaro/miniserve/releases/download/${MINISERVE_TAG}/${asset}"
  if [[ -f "${dest}" ]] && [[ "${SKIP_DOWNLOAD}" -eq 1 ]]; then
    echo "reuse ${dest}"
    return 0
  fi
  echo "download ${asset}"
  curl -fsSL "${url}" -o "${dest}"
}

echo "==> Checking dataset"
if [[ ! -d "${IMAGES_SRC}" ]]; then
  echo "error: missing ${IMAGES_SRC}; build data/exif_images first" >&2
  exit 1
fi
image_count="$(find "${IMAGES_SRC}" -maxdepth 1 -name '*.jpg' | wc -l | tr -d ' ')"
if [[ "${image_count}" -eq 0 ]]; then
  echo "error: no JPEGs in ${IMAGES_SRC}" >&2
  exit 1
fi
echo "    ${image_count} JPEGs"

echo "==> Exporting map index (${PROFILE})"
if [[ -x "${PYTHON}" ]]; then
  "${PYTHON}" scripts/export_map_index.py --profile "${PROFILE}"
else
  python3 scripts/export_map_index.py --profile "${PROFILE}"
fi

if [[ "${SKIP_NPM}" -eq 0 ]]; then
  echo "==> Building web app"
  require_cmd npm
  (
    cd "${WEB_DIR}"
    if [[ -f package-lock.json ]]; then
      npm ci
    else
      npm install
    fi
    npm run build
  )
fi

if [[ ! -f "${DIST_DIR}/index.html" ]]; then
  echo "error: missing ${DIST_DIR}/index.html; run npm run build in web/exif-map" >&2
  exit 1
fi

echo "==> Staging ${STAGING}"
rm -rf "${STAGING}"
mkdir -p "${STAGING}/site/dataset/images" "${STAGING}/bin"

cp -a "${DIST_DIR}/." "${STAGING}/site/"
cp -a "${IMAGES_SRC}/." "${STAGING}/site/dataset/images/"

echo "==> Downloading miniserve ${MINISERVE_TAG}"
require_cmd curl
download_miniserve "miniserve-${MINISERVE_TAG#v}-x86_64-pc-windows-msvc.exe" \
  "${STAGING}/bin/miniserve-windows-x86_64.exe"
download_miniserve "miniserve-${MINISERVE_TAG#v}-x86_64-apple-darwin" \
  "${STAGING}/bin/miniserve-macos-x86_64"
download_miniserve "miniserve-${MINISERVE_TAG#v}-aarch64-apple-darwin" \
  "${STAGING}/bin/miniserve-macos-aarch64"
download_miniserve "miniserve-${MINISERVE_TAG#v}-x86_64-unknown-linux-gnu" \
  "${STAGING}/bin/miniserve-linux-x86_64"
chmod +x \
  "${STAGING}/bin/miniserve-macos-x86_64" \
  "${STAGING}/bin/miniserve-macos-aarch64" \
  "${STAGING}/bin/miniserve-linux-x86_64"

cat >"${STAGING}/README.txt" <<EOF
EXIF flood image map viewer (${VERSION})

1. Unzip this folder anywhere.
2. Double-click the launcher for your system:
   - Windows: Start EXIF Map.bat
   - macOS:   Start EXIF Map.command
   - Linux:   start-exif-map.sh
3. Your browser opens http://127.0.0.1:${PORT}

No Python or Node.js required. Stop the server by closing the terminal window
(Windows/macOS) or pressing Ctrl+C in the terminal (Linux).

Dataset: ${image_count} geotagged JPEGs with flood ML metadata.
EOF

cat >"${STAGING}/Start EXIF Map.bat" <<EOF
@echo off
cd /d "%~dp0"
start /B "" bin\\miniserve-windows-x86_64.exe site -p ${PORT} --index index.html
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:${PORT}"
echo EXIF map running at http://127.0.0.1:${PORT}
echo Close this window to stop the server.
pause
EOF

cat >"${STAGING}/Start EXIF Map.command" <<EOF
#!/bin/bash
set -euo pipefail
cd "\$(dirname "\$0")"
case "\$(uname -m)" in
  arm64) BIN=bin/miniserve-macos-aarch64 ;;
  *)     BIN=bin/miniserve-macos-x86_64 ;;
esac
chmod +x "\$BIN"
open "http://127.0.0.1:${PORT}"
exec "\$BIN" site -p ${PORT} --index index.html
EOF
chmod +x "${STAGING}/Start EXIF Map.command"

cat >"${STAGING}/start-exif-map.sh" <<EOF
#!/bin/bash
set -euo pipefail
cd "\$(dirname "\$0")"
chmod +x bin/miniserve-linux-x86_64
if command -v xdg-open >/dev/null 2>&1; then
  (sleep 1 && xdg-open "http://127.0.0.1:${PORT}") &
elif command -v gio >/dev/null 2>&1; then
  (sleep 1 && gio open "http://127.0.0.1:${PORT}") &
fi
echo "EXIF map at http://127.0.0.1:${PORT} (Ctrl+C to stop)"
exec bin/miniserve-linux-x86_64 site -p ${PORT} --index index.html
EOF
chmod +x "${STAGING}/start-exif-map.sh"

echo "==> Creating ${ZIP_PATH}"
mkdir -p "${ROOT}/release"
rm -f "${ZIP_PATH}"

if command -v zip >/dev/null 2>&1; then
  (
    cd "${ROOT}/release"
    zip -r -q "$(basename "${ZIP_PATH}")" "$(basename "${STAGING}")"
  )
else
  echo "    zip not found; using python3"
  STAGING="${STAGING}" ZIP_PATH="${ZIP_PATH}" python3 <<'PY'
import os
import zipfile
from pathlib import Path

staging = Path(os.environ["STAGING"])
zip_path = Path(os.environ["ZIP_PATH"])
root_name = staging.name

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            zf.write(path, Path(root_name) / path.relative_to(staging))
PY
fi

if command -v sha256sum >/dev/null 2>&1; then
  CHECKSUM="$(sha256sum "${ZIP_PATH}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  CHECKSUM="$(shasum -a 256 "${ZIP_PATH}" | awk '{print $1}')"
else
  CHECKSUM=""
fi

echo ""
echo "Done."
echo "  Staging:  ${STAGING}"
echo "  Zip:      ${ZIP_PATH}"
echo "  Size:     $(du -h "${ZIP_PATH}" | awk '{print $1}')"
if [[ -n "${CHECKSUM}" ]]; then
  echo "  SHA256:   ${CHECKSUM}"
  echo ""
  echo "Attach to GitHub Release ${VERSION}:"
  echo "  gh release upload ${VERSION} \"${ZIP_PATH}\" --clobber"
fi
