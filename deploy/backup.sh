#!/bin/sh
# Dumps the VeriLedger database of deploy/docker-compose.prod.yml (VLA-28), from the repository root.
# Usage: deploy/backup.sh [file], backups/veriledger-<UTC time>.dump by default. Restore it with deploy/restore.sh.
set -eu

target="${1:-backups/veriledger-$(date -u +%Y%m%dT%H%M%SZ).dump}"
mkdir -p "$(dirname "$target")"

# pg_dump runs inside the postgres container with its own credentials; -Fc is compressed, and what pg_restore reads
docker compose -f deploy/docker-compose.prod.yml exec -T postgres \
  sh -c 'pg_dump --format=custom --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' > "$target"

[ -s "$target" ] || { echo "backup: $target is empty" >&2; exit 1; }
echo "backup: $target ($(wc -c < "$target") bytes)"
