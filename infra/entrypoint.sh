#!/usr/bin/env bash
set -euo pipefail

echo "==> Running Django migrations..."
uv run python manage.py migrate --no-input

echo "==> Seeding catalog (plans, products)..."
uv run python manage.py seed_catalog

echo "==> Collecting static files..."
uv run python manage.py collectstatic --no-input

echo "==> Starting uvicorn..."
exec uv run uvicorn config.asgi:application \
    --host 0.0.0.0 \
    --port "${DJANGO_PORT:-8001}" \
    --log-config /app/infra/uvicorn-log-config.json \
    --workers 4
