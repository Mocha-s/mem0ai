# Production image for the mem0 OSS V3 server.
# Build context MUST be the repo root (set in compose: `context: ..`)
# so we can pip install the local mem0/ SDK with V3 fixes that are not on PyPI.

# ---- builder ----
# Stay on slim — modern psycopg/pgvector/bcrypt all ship wheels for
# linux/amd64 so no gcc needed. If a future dep does need compilation,
# add `apt-get install -y --no-install-recommends build-essential`
# (mind apt mirror flakiness — may need retries).
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /build

# Install local mem0 SDK first (bigger, rarely changes vs server code).
# `--user` keeps everything under /root/.local for easy copy to runtime stage.
COPY pyproject.toml README.md ./
COPY mem0 ./mem0
RUN pip install --user .

# Server-specific deps on top of mem0's transitive set.
COPY server/requirements.txt server-requirements.txt
RUN pip install --user -r server-requirements.txt

# ---- runtime ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/mem0/.local/bin:$PATH \
    PYTHONPATH=/app

# curl for the /v1/ping/ HEALTHCHECK; libpq for psycopg.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /bin/bash mem0

# Bring installed Python packages from builder.
COPY --from=builder --chown=mem0:mem0 /root/.local /home/mem0/.local

WORKDIR /app

# Server source — only what the runtime needs. Notably excluded:
#   .env (secrets — must come from env_file at runtime)
#   data/, history/ (host bind mounts)
#   dashboard/ (separate image)
#   tests/ (dev-only)
#   init-db.sh (mounted into the postgres container, not this one)
#   docker-compose.yaml, dev.Dockerfile, Dockerfile (build artifacts)
COPY --chown=mem0:mem0 server/main.py \
                       server/auth.py \
                       server/db.py \
                       server/errors.py \
                       server/models.py \
                       server/rate_limit.py \
                       server/schemas.py \
                       server/server_state.py \
                       server/telemetry.py \
                       server/alembic.ini \
                       ./
COPY --chown=mem0:mem0 server/routers ./routers
COPY --chown=mem0:mem0 server/alembic ./alembic

USER mem0

EXPOSE 8000

# Image-level healthcheck (compose may override with the same shape).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fs http://localhost:8000/v1/ping/ || exit 1

# Apply migrations, then serve. 2 uvicorn workers — small box, leaves
# headroom for postgres + dashboard. Tune via compose if needed.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2"]
