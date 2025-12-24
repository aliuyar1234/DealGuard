# ===========================================
# DealGuard Backend Dockerfile
# ===========================================

# Base stage with runtime dependencies
ARG PYTHON_IMAGE=python:3.12.8-slim
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL runtime client
    libpq5 \
    # PDF processing
    poppler-utils \
    # OCR
    tesseract-ocr \
    tesseract-ocr-deu \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# ===========================================
# Builder stage
# ===========================================
FROM base AS builder

# Build tools for compiling wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and source (needed for build)
COPY pyproject.toml README.md ./
COPY src ./src

# Install production dependencies into /install
RUN pip install --no-cache-dir --prefix=/install .

# ===========================================
# Development stage
# ===========================================
FROM builder AS development

# Copy source code (including tests/dev tooling)
COPY . .

# Install dependencies (with dev)
RUN pip install --no-cache-dir -e ".[dev]"

# Default command
CMD ["uvicorn", "dealguard.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===========================================
# Production stage
# ===========================================
FROM base AS production

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

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

# Stop signal for graceful shutdown
STOPSIGNAL SIGTERM

# Default command
CMD ["uvicorn", "dealguard.main:app", "--host", "0.0.0.0", "--port", "8000"]
