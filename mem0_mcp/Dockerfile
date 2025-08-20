# Production Dockerfile for Mem0 MCP Server
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r mem0user && useradd -r -g mem0user mem0user

# Create app directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy only necessary files
COPY src/ ./src/
COPY config/ ./config/
COPY run_server_production.py .

# Create logs directory with proper permissions
RUN mkdir -p /app/logs && chown -R mem0user:mem0user /app

# Switch to non-root user
USER mem0user

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${MCP_PORT:-8080}/health || exit 1

# Expose port
EXPOSE 8080

# Production command
CMD ["python3", "run_server_production.py"]