#!/usr/bin/env sh
# Applies database migrations, then starts the API.
set -eu

: "${API_PORT:?API_PORT must be set}"
: "${API_WORKERS:?API_WORKERS must be set}"
: "${FORWARDED_ALLOW_IPS:?FORWARDED_ALLOW_IPS must be set}"
: "${TZ:?TZ must be set}"

echo "[entrypoint] applying migrations"
alembic upgrade head

echo "[entrypoint] starting API on :${API_PORT} with ${API_WORKERS} workers (TZ=${TZ})"
# --proxy-headers + --forwarded-allow-ips: trust X-Forwarded-For only from our own proxy (nginx),
# so the real client IP is used for rate limiting and audit logs.
exec uvicorn chitbook_api.main:app \
    --host 0.0.0.0 \
    --port "${API_PORT}" \
    --workers "${API_WORKERS}" \
    --proxy-headers \
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS}" \
    --no-access-log \
    --no-server-header
