# Base image
FROM python:3.14-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ="Europe/Istanbul"

# Work directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create volume for database and logs
VOLUME ["/app/data", "/app/logs"]

# Default command (can be overridden)
CMD ["python", "main.py"]
