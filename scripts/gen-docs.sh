#!/usr/bin/env bash
# Regenerates the generated docs (docs/api/*.md except README.md, docs/database.md):
#   1. runs the API tests while recording the SQL tables each endpoint touches
#   2. builds the markdown from the code + that recording
# Run after changing any endpoint, schema, model, error code or log event.
set -euo pipefail

cd "$(dirname "$0")/.."
(cd apps/api && TRACE_SQL_TABLES="$PWD/../../docs/api/.endpoint-tables.json" .venv/bin/pytest -q -p no:warnings)
apps/api/.venv/bin/python scripts/gen_api_docs.py
