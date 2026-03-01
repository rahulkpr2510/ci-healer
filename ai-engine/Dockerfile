# ai-engine/Dockerfile
# Multi-stage build for the LangGraph AI engine

# ── Stage 1: Builder ──────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Build deps: gcc for native extensions (grpcio, cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime deps: git (for cloning/committing repos), Node.js optional linters
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libssl3 \
    libffi8 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages
COPY --from=builder /install /usr/local

# Copy source
COPY . .

# Create workspace directories for cloned repos.
# Both paths are created so the default (/app/workspace) and any
# WORKSPACE_DIR=/workspace override in Render env vars both work.
RUN mkdir -p /app/workspace /workspace

# Non-root user
RUN useradd -m appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /workspace
USER appuser

# Expose engine port
EXPOSE 8001

# ── Startup ───────────────────────────────────────────────
# Pre-compiles the LangGraph on boot via lifespan handler.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
