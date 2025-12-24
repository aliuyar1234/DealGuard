#!/bin/sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

if [ -z "${S3_ENDPOINT:-}" ] || [ -z "${S3_BUCKET:-}" ]; then
  echo "S3_ENDPOINT and S3_BUCKET must be set" >&2
  exit 1
fi

if [ -n "${S3_ACCESS_KEY_FILE:-}" ]; then
  if [ ! -r "$S3_ACCESS_KEY_FILE" ]; then
    echo "S3_ACCESS_KEY_FILE is not readable: $S3_ACCESS_KEY_FILE" >&2
    exit 1
  fi
  S3_ACCESS_KEY="$(cat "$S3_ACCESS_KEY_FILE")"
fi

if [ -n "${S3_SECRET_KEY_FILE:-}" ]; then
  if [ ! -r "$S3_SECRET_KEY_FILE" ]; then
    echo "S3_SECRET_KEY_FILE is not readable: $S3_SECRET_KEY_FILE" >&2
    exit 1
  fi
  S3_SECRET_KEY="$(cat "$S3_SECRET_KEY_FILE")"
fi

if [ -z "${S3_ACCESS_KEY:-}" ] || [ -z "${S3_SECRET_KEY:-}" ]; then
  echo "S3_ACCESS_KEY and S3_SECRET_KEY must be set" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR/$S3_BUCKET"

until mc alias set backup "$S3_ENDPOINT" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" >/dev/null 2>&1; do
  sleep 2
done

while true; do
  timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
  target_dir="$BACKUP_DIR/$S3_BUCKET/$timestamp"
  mkdir -p "$target_dir"
  mc mirror --overwrite "backup/$S3_BUCKET" "$target_dir"

  find "$BACKUP_DIR/$S3_BUCKET" -mindepth 1 -maxdepth 1 -type d -mtime +"$BACKUP_RETENTION_DAYS" -exec rm -rf {} +
  sleep "$BACKUP_INTERVAL_SECONDS"
done
