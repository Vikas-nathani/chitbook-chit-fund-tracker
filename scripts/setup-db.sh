#!/usr/bin/env bash
# One-time (re-runnable) setup of the ChitBook database on the host Postgres.
#   - creates the app role + main and test databases (infra/postgres/setup.sql)
#   - allows the Docker subnet in pg_hba.conf for the app role only, then reloads Postgres
# Usage: scripts/setup-db.sh        (run from the repo root; needs sudo for pg_hba.conf)
set -euo pipefail

cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1091
source .env
set +a

: "${POSTGRES_SUPERUSER:?}" "${POSTGRES_SUPERUSER_PASSWORD:?}" "${POSTGRES_SETUP_HOST:?}"
: "${DB_PORT:?}" "${DB_NAME:?}" "${DB_TEST_NAME:?}" "${DB_USER:?}" "${DB_PASSWORD:?}" "${TZ:?}" "${DOCKER_SUBNET:?}"

export PGPASSWORD="$POSTGRES_SUPERUSER_PASSWORD"
PSQL=(psql -h "$POSTGRES_SETUP_HOST" -p "$DB_PORT" -U "$POSTGRES_SUPERUSER" -d postgres -v ON_ERROR_STOP=1 -q)

echo "[setup-db] creating role/databases"
"${PSQL[@]}" \
  -v app_user="$DB_USER" -v app_password="$DB_PASSWORD" \
  -v db_name="$DB_NAME" -v test_db_name="$DB_TEST_NAME" -v tz="$TZ" \
  -f infra/postgres/setup.sql

HBA_FILE=$("${PSQL[@]}" -tAc "SHOW hba_file")
for db in "$DB_NAME" "$DB_TEST_NAME"; do
  LINE="host    ${db}    ${DB_USER}    ${DOCKER_SUBNET}    scram-sha-256   # chitbook docker network"
  if sudo grep -qF "$LINE" "$HBA_FILE"; then
    echo "[setup-db] pg_hba already allows ${db} from ${DOCKER_SUBNET}"
  else
    echo "[setup-db] adding to ${HBA_FILE}: ${LINE}"
    echo "$LINE" | sudo tee -a "$HBA_FILE" >/dev/null
  fi
done
"${PSQL[@]}" -tAc "SELECT pg_reload_conf()" >/dev/null

echo "[setup-db] checking app login"
PGPASSWORD="$DB_PASSWORD" psql -h "$POSTGRES_SETUP_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT 'ok: ' || current_user || ' @ ' || current_database() || ' tz=' || current_setting('TimeZone')"
