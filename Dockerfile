# Multi-stage build for a lighter final image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install python dependencies in a virtual env
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY epic-4/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and install the package
COPY epic-4/ .
RUN pip install .

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install git (runtime dependency)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy source code for runtime reference (if needed, though installed as package)
COPY epic-4/epic4/ ./epic4/
COPY epic-4/application.py ./application.py
# Create artifacts directory structure required by the app
RUN mkdir -p artifacts/docs artifacts/summaries artifacts/logs

# Set environment keys for python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose HTTP port for FastAPI
EXPOSE 8000

# Run FastAPI application
CMD ["uvicorn", "epic4.api:app", "--host", "0.0.0.0", "--port", "8000"]
