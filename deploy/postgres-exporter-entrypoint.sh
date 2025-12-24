#!/bin/sh
set -eu

if [ -z "${DATABASE_SYNC_URL_FILE:-}" ]; then
  echo "DATABASE_SYNC_URL_FILE is required" >&2
  exit 1
fi

if [ ! -r "$DATABASE_SYNC_URL_FILE" ]; then
  echo "DATABASE_SYNC_URL_FILE is not readable: $DATABASE_SYNC_URL_FILE" >&2
  exit 1
fi

DATA_SOURCE_NAME="$(cat "$DATABASE_SYNC_URL_FILE")"
export DATA_SOURCE_NAME

exec /bin/postgres_exporter
