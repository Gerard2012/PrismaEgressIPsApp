# Use a lightweight Python base image
FROM python:3.12-slim

# Avoid interactive prompts and enable Python best practices
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Build arguments to align container user with host user
ARG UID=1000
ARG GID=1000

# Create group and user with matching UID/GID
RUN groupadd -g ${GID} appgroup \
    && useradd -m -u ${UID} -g ${GID} appuser

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application source files
COPY src/ /app/src/

# Ensure app directory (and logs) are owned by appuser
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 5000

# Default command — can be overridden in docker-compose
CMD ["python", "src/main.py"]