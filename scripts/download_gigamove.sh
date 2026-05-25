#!/usr/bin/env bash
# Download GIA social media datasets from GigaMove into data/raw.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW="${ROOT}/data/raw"
COOKIE="${RAW}/.gigamove_cookies.txt"
mkdir -p "${RAW}"

download_id() {
  local id="$1"
  local out_name="$2"
  local out_path="${RAW}/${out_name}"

  if [[ -f "${out_path}" ]]; then
    echo "skip (exists): ${out_name}"
    return 0
  fi

  curl -fsSL -c "${COOKIE}" -b "${COOKIE}" \
    "https://gigamove.rwth-aachen.de/en/download/${id}" -o /dev/null

  local cephfs_url
  cephfs_url="$(
    curl -fsSL -c "${COOKIE}" -b "${COOKIE}" \
      -H "Accept: application/json" \
      -H "X-Requested-With: XMLHttpRequest" \
      "https://gigamove.rwth-aachen.de/en/download/cephfs-link/${id}" \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['download_url'])"
  )"

  echo "downloading: ${out_name}"
  curl -fL -C - -c "${COOKIE}" -b "${COOKIE}" \
    "${cephfs_url}" -o "${out_path}.part"
  mv "${out_path}.part" "${out_path}"
  echo "done: ${out_name}"
}

# Posts last 3 years (JSON, no images)
download_id "db666e8f10cbb95fee7ee363084fabf0" "posts_only.zip"

# Legacy Flickr data with geom polygons (~2.6 GB)
download_id "dffd3f56179b565b78fad787c6c7e9e4" "legacy_flickr.json"

# 2023 sample with images (53 GB) — skip if already present
if [[ ! -f "${RAW}/social_media_2023-2024.zip" ]]; then
  download_id "e5b00930def8870289fc98057b3f3434" "social_media_2023-2024.zip"
else
  echo "skip (exists): social_media_2023-2024.zip"
fi
