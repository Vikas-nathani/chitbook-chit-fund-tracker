#!/usr/bin/env bash
# Regenerates the mobile app's API types from the running API's OpenAPI schema.
# Run after any API request/response change:   scripts/gen-api-types.sh
set -euo pipefail

cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1091
source .env
set +a

OUT=apps/mobile/src/api/schema.d.ts
URL="http://localhost:${API_PORT}/api/openapi.json"

echo "[gen-api-types] reading ${URL}"
npx -y openapi-typescript@7 "$URL" -o "$OUT"
echo "[gen-api-types] wrote ${OUT}"
