#!/bin/sh
set -eu

if [ -n "${REDIS_PASSWORD_FILE:-}" ]; then
  if [ ! -r "$REDIS_PASSWORD_FILE" ]; then
    echo "REDIS_PASSWORD_FILE is not readable: $REDIS_PASSWORD_FILE" >&2
    exit 1
  fi
  REDIS_PASSWORD="$(cat "$REDIS_PASSWORD_FILE")"
fi

if [ -z "${REDIS_ADDR:-}" ]; then
  REDIS_ADDR="redis://redis:6379"
fi

if [ -n "${REDIS_PASSWORD:-}" ]; then
  export REDIS_PASSWORD
fi

export REDIS_ADDR

exec /bin/redis_exporter
