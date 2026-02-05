# Multi-stage Dockerfile for oap-langgraph-tools-agent using UV
# Stage 1: Builder - install dependencies and build virtual environment
FROM python:3.12-slim AS builder

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies with cache mount for faster builds
# Using --no-dev for production, but for v0.0.0 we need dev dependencies
# (langgraph-cli is a dev dependency required for `langgraph dev` command)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

# Copy application source
COPY tools_agent/ ./tools_agent/
COPY langgraph.json ./

# Install the application in non-editable mode (for production)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

# Stage 2: Runtime - minimal image with only necessary files
FROM python:3.12-slim AS runtime

# Install system dependencies for SSL certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code (excluding development files)
COPY --from=builder /app/tools_agent/ ./tools_agent/
COPY --from=builder /app/langgraph.json ./

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED="1"
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Create writable directory for langgraph runtime data and set ownership
RUN mkdir -p /app/.langgraph_api && chown -R appuser:appuser /app/.langgraph_api
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose LangGraph dev server port (default: 2024)
EXPOSE 2024

# Health check - verify server is responding
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import sys; import urllib.request; urllib.request.urlopen('http://localhost:2024/', timeout=2)" || exit 1

# Default command: run LangGraph dev server
# Note: langgraph CLI is installed via langgraph-cli (dev dependency)
CMD ["langgraph", "dev", "--no-browser"]

# Build instructions:
# 1. For development/testing (includes dev dependencies):
#    docker build -t oap-langgraph-tools-agent:test .
#
# 2. For production (without dev dependencies - requires different CMD):
#    Modify builder stage to use `uv sync --frozen --no-dev --no-editable`
#    And update CMD to use a production entrypoint
