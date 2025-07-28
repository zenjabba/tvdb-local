# Base stage with common dependencies
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# API stage (default)
FROM base AS api
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Worker stage
FROM base AS worker
USER app
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]

# Scheduler stage
FROM base AS scheduler
USER app
CMD ["celery", "-A", "app.workers.celery_app", "beat", "--loglevel=info"]

# Default stage
FROM api