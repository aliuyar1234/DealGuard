#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

if [ -z "${PGHOST:-}" ] || [ -z "${PGDATABASE:-}" ] || [ -z "${PGUSER:-}" ]; then
  echo "PGHOST, PGDATABASE, and PGUSER must be set" >&2
  exit 1
fi

if [ -n "${PGPASSWORD_FILE:-}" ]; then
  if [ ! -r "$PGPASSWORD_FILE" ]; then
    echo "PGPASSWORD_FILE is not readable: $PGPASSWORD_FILE" >&2
    exit 1
  fi
  export PGPASSWORD="$(cat "$PGPASSWORD_FILE")"
fi

mkdir -p "$BACKUP_DIR"

while true; do
  timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
  backup_file="${BACKUP_DIR}/pg_${PGDATABASE}_${timestamp}.dump"
  pg_dump -Fc --no-owner --no-privileges > "$backup_file"

  find "$BACKUP_DIR" -type f -name "pg_${PGDATABASE}_*.dump" -mtime +"$BACKUP_RETENTION_DAYS" -delete
  sleep "$BACKUP_INTERVAL_SECONDS"
done
