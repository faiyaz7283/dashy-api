#!/bin/sh
set -e

# Run database migrations
echo "Running database migrations..."
uv run alembic upgrade head

# Start the application
echo "Starting application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
