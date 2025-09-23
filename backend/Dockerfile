# ALS Assistant Backend Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Accept USER_ID and GROUP_ID as build arguments
ARG USER_ID=1000
ARG GROUP_ID=1000

# Create user with the same UID/GID as the host user
RUN groupadd -g ${GROUP_ID} appuser && \
    useradd -u ${USER_ID} -g ${GROUP_ID} -r appuser

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with updated bcrypt for compatibility
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir bcrypt==4.1.3 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create data directory and set proper permissions
RUN mkdir -p /app/app/data && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Copy data files with proper permissions
COPY --chown=appuser:appuser app/data/*.json /app/app/data/
COPY --chown=appuser:appuser app/data/*.sql /app/app/data/
COPY --chown=appuser:appuser app/data/als.db /app/app/data/als.db

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production
ENV LOG_LEVEL=INFO

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Improved health check using the correct endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/livez || exit 1

# Run the application with production settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]