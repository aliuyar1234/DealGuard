#!/bin/sh
set -eu

if [ -n "${REDIS_PASSWORD_FILE:-}" ]; then
  if [ ! -r "$REDIS_PASSWORD_FILE" ]; then
    echo "REDIS_PASSWORD_FILE is not readable: $REDIS_PASSWORD_FILE" >&2
    exit 1
  fi
  REDIS_PASSWORD="$(cat "$REDIS_PASSWORD_FILE")"
fi

if [ -z "${REDIS_PASSWORD:-}" ]; then
  echo "REDIS_PASSWORD is required" >&2
  exit 1
fi

exec redis-server --appendonly yes --requirepass "$REDIS_PASSWORD"
