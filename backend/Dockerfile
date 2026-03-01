# backend/Dockerfile
# Multi-stage build for production FastAPI backend

# ── Stage 1: Builder ──────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps into a prefix we can copy later
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime only: libpq for asyncpg / psycopg2, git for agent operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose backend port
EXPOSE 8000

# ── Startup ───────────────────────────────────────────────
# In production: run migrations first, then start the server.
# APP_ENV=production triggers Alembic path in lifespan (init_db is skipped).
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
