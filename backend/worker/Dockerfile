FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY worker/ ./worker/
COPY homelab/ ./homelab/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV WORKER_MODE=worker
ENV ALLOW_CLOUD_LLM=false

# Run worker
CMD ["python", "-m", "worker.main"]
