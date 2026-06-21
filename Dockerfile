# Multi-stage build for a lighter final image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install git (runtime dependency)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy source code for runtime reference
COPY src/ ./src/
COPY application.py ./application.py

# Create artifacts directory structure required by the app and adjust ownership
RUN mkdir -p artifacts/docs artifacts/summaries artifacts/logs && \
    chown -R nobody:nogroup /app artifacts

# Set environment keys for python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose HTTP port for FastAPI
EXPOSE 8000

# Run container as non-root
USER nobody

# Native python health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request, os; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

# Run FastAPI application
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
