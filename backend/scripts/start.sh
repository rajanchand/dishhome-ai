#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting DishHome AI Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
