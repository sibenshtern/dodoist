#!/bin/bash
# Waits for the database then applies migrations before starting the server.
set -e

echo "[backend] Waiting for database..."
until python manage.py migrate --noinput 2>&1; do
    echo "[backend] Database not ready — retrying in 2s..."
    sleep 2
done
echo "[backend] Migrations applied."

exec "$@"
