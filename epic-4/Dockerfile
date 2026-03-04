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

# Copy source code and install the package
COPY . .
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
COPY epic4/ ./epic4/
COPY application.py ./application.py
# Create artifacts directory structure required by the app
RUN mkdir -p artifacts/docs artifacts/summaries artifacts/logs

# Set environment keys for python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Expose port for FastAPI (health/optional API mode)
EXPOSE 8000

# Default command runs EPIC-4 queue worker.
CMD ["python", "-m", "epic4.service_bus_worker"]
