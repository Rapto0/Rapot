# Base image
FROM python:3.12.8-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ="Europe/Istanbul"

# Work directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt requirements-dev.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements-dev.lock \
    && pip check

# Copy project files
COPY . .

# Default command (can be overridden)
CMD ["python", "-m", "scripts.runtime", "bot"]
