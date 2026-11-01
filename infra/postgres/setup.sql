-- One-time setup of the ChitBook database on the host Postgres.
-- Run by scripts/setup-db.sh as the Postgres superuser. Safe to re-run.
-- psql variables (passed with -v): app_user, app_password, db_name, test_db_name, tz

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec

-- Keep the password in sync with .env on every run
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'app_user', :'app_password')
\gexec

-- Every session of the app role uses IST
SELECT format('ALTER ROLE %I SET timezone = %L', :'app_user', :'tz')
\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'db_name', :'app_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db_name')
\gexec

SELECT format('CREATE DATABASE %I OWNER %I', :'test_db_name', :'app_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'test_db_name')
\gexec

-- Only the owner (app role) may connect; nobody else gets default access
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'db_name')
\gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'test_db_name')
\gexec
