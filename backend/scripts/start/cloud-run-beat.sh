#!/bin/bash
set -e -x

python -m http.server "${PORT:-8080}" --bind 0.0.0.0 --directory /tmp &
HEALTH_PID=$!
trap 'kill "${HEALTH_PID}" 2>/dev/null || true' EXIT

rm -f './celerybeat.pid'
exec uv run celery -A app.main:celery_app beat -l info
