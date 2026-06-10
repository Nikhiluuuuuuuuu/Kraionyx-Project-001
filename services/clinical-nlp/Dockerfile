# Stage 1: Build
FROM python:3.11-slim@sha256:a6fce523c0bdfed5e1b203c73fc5a2105151b54a2608358ea82200dc89dbb166 AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim@sha256:a6fce523c0bdfed5e1b203c73fc5a2105151b54a2608358ea82200dc89dbb166

# Create non-root user
RUN addgroup --system appgroup && adduser --system --group appuser

WORKDIR /app

# Install curl for HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install runtime dependencies
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy application code
COPY src/ ./src/

# Change ownership
RUN chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8002/metrics || exit 1

CMD ["python", "src/main.py"]
