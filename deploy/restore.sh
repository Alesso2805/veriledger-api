#!/bin/sh
# Restores a dump of deploy/backup.sh into the database of deploy/docker-compose.prod.yml, from the
# repository root. It replaces what the database holds, so the API is stopped first and started again after.
# Usage: deploy/restore.sh <file>
set -eu

dump="${1:?usage: deploy/restore.sh <file>}"
[ -s "$dump" ] || { echo "restore: $dump is missing or empty" >&2; exit 1; }

compose="docker compose -f deploy/docker-compose.prod.yml"
$compose stop api
# --clean --if-exists drops what the dump holds before recreating it, whether or not it is still there
$compose exec -T postgres \
  sh -c 'pg_restore --clean --if-exists --no-owner --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' < "$dump"
$compose start api
echo "restore: $dump is back"
