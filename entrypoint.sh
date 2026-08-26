#!/bin/sh
set -e

# Wait for PostgreSQL to be ready before running migrations
echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
until uv run python -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(
        user=os.environ.get('POSTGRES_USER', 'dashy'),
        password=os.environ.get('POSTGRES_PASSWORD', 'dashy'),
        database=os.environ.get('POSTGRES_DB', 'dashy'),
        host=os.environ.get('POSTGRES_HOST', 'postgres'),
        port=int(os.environ.get('POSTGRES_PORT', 5432)),
    )
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL ready. Running migrations..."

# Run database migrations
uv run alembic upgrade head

# Start the application
echo "Starting application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
