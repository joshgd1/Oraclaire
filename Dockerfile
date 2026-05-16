# Oraclaire — Backend API (Nexus)
# Multi-stage: builder + runtime

FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies (install project for Python path)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen

# Copy source
COPY src/ src/
COPY alembic/ alembic/
COPY data/ data/

# Create non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

ENV PYTHONUNBUFFERED=1
ENV NEXUS_API_BASE_URL=http://localhost:8000

ENTRYPOINT ["uv", "run", "python", "-m", "src.server.app"]
