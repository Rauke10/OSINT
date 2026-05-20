# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Stage 0 — frontend: build the React SPA into the Python package's static/.
# ---------------------------------------------------------------------------
FROM node:22-bookworm-slim AS frontend

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci
COPY frontend ./frontend
# Vite emits the built SPA to /app/src/globeye/api/static (see vite.config.ts).
RUN cd frontend && npm run build

# ---------------------------------------------------------------------------
# Stage 1 — builder: resolve deps into a relocatable virtualenv with uv.
# The uv image ships a relocatable (python-build-standalone) interpreter,
# so the resulting venv can be copied into a distroless runtime.
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Layer 1: dependencies only (cached unless deps change).
COPY pyproject.toml ./
COPY uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

# Layer 2: project source + the built web UI.
COPY src ./src
COPY --from=frontend /app/src/globeye/api/static ./src/globeye/api/static
COPY README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# ---------------------------------------------------------------------------
# Stage 2 — runtime: distroless, non-root (UID 10001), no shell, no pkg mgr.
# distroless/cc provides the glibc the standalone interpreter needs.
# ---------------------------------------------------------------------------
FROM gcr.io/distroless/cc-debian12:nonroot AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GLOBEYE_CACHE_DIR=/data/cache \
    GLOBEYE_DB_URL=sqlite:////data/globeye.db

COPY --from=builder /usr/local/bin/python* /usr/local/bin/
COPY --from=builder --chown=10001:10001 /app /app

WORKDIR /app
# Numeric non-root UID; /data and /tmp are the only writable paths (see compose).
USER 10001:10001
EXPOSE 8000

ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["--factory", "globeye.api.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
