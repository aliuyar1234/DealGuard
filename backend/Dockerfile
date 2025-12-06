# ===========================================
# DealGuard Backend Dockerfile
# ===========================================

# Base stage with system dependencies
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    build-essential \
    # PostgreSQL client
    libpq-dev \
    # PDF processing
    poppler-utils \
    # OCR
    tesseract-ocr \
    tesseract-ocr-deu \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# ===========================================
# Development stage
# ===========================================
FROM base AS development

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and README (needed for hatchling build)
COPY pyproject.toml README.md ./

# Install dependencies (with dev)
RUN uv pip install --system -e ".[dev]"

# Copy source code
COPY . .

# Default command
CMD ["uvicorn", "dealguard.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===========================================
# Production stage
# ===========================================
FROM base AS production

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files and README (needed for hatchling build)
COPY pyproject.toml README.md ./

# Install production dependencies only
RUN uv pip install --system -e .

# Copy source code
COPY src ./src

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')"

# Default command
CMD ["uvicorn", "dealguard.main:app", "--host", "0.0.0.0", "--port", "8000"]
