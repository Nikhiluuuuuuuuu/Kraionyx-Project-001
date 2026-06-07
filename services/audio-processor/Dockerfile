# --------------------------------------------------------------------------
# Kraionyx Audio Processor — CPU Dockerfile
# --------------------------------------------------------------------------
FROM python:3.11-slim AS base

LABEL maintainer="Kraionyx Team" \
      service="audio-processor" \
      description="GPU-optional audio preprocessing microservice"

# System dependencies required by soundfile, ffmpeg, and numpy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        libsndfile1-dev \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security (HIPAA requirement)
RUN groupadd -r kraionyx && useradd -r -g kraionyx -m -s /bin/bash kraionyx

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install shared library
COPY ../../shared/python /tmp/kraionyx-common
RUN pip install --no-cache-dir /tmp/kraionyx-common && \
    rm -rf /tmp/kraionyx-common

# Copy application code
COPY src/ ./src/

# Switch to non-root user
USER kraionyx

# Health-check (process is alive)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEVICE=cpu

ENTRYPOINT ["python", "-m", "src.main"]
