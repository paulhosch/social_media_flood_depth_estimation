#!/usr/bin/env bash
# Build data/canonical/ from GIA raw JSON under data/raw/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

exec python3 -m catalogue.build "$@"
