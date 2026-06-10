# --------------------------------------------------------------------------
# Svaani Audio Processor — CPU Dockerfile
# --------------------------------------------------------------------------
FROM python:3.11-slim@sha256:a6fce523c0bdfed5e1b203c73fc5a2105151b54a2608358ea82200dc89dbb166 AS base

LABEL maintainer="Svaani Team" \
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
RUN groupadd -r svaani && useradd -r -g svaani -m -s /bin/bash svaani

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install shared library
COPY ../../shared/python /tmp/svaani-common
RUN pip install --no-cache-dir /tmp/svaani-common && \
    rm -rf /tmp/svaani-common

# Copy application code
COPY src/ ./src/

# Switch to non-root user
USER svaani

# Health-check (process is alive)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEVICE=cpu

ENTRYPOINT ["python", "-m", "src.main"]
