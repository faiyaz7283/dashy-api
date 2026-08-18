FROM python:3.13-slim AS build

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application
COPY . .

FROM python:3.13-slim

WORKDIR /app

# Copy UV and dependencies from build
COPY --from=build /usr/local/bin/uv /usr/local/bin/uv
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app /app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Copy and use entrypoint script for migrations
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
