# ChitBook API image. All configuration comes from the environment at runtime (.env).

# ---------- build: install dependencies into a virtualenv with uv ----------
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first so code changes don't invalidate this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# ---------- runtime ----------
FROM python:3.13-slim AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app /app
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && useradd --system --no-create-home chitbook
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Logs go to stdout only, so the app needs no writable directory
USER chitbook

# Liveness only (no DB): the container is up if the process answers
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS "http://localhost:${API_PORT}/health" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
