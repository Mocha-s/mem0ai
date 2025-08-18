# Mem0 MCP Server - Simplified Dockerfile
FROM python:3.11-slim

# Set environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH="/app/src"

# Install system dependencies (minimal set)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 mem0 && \
    useradd --uid 1000 --gid mem0 --shell /bin/bash --create-home mem0

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY --chown=mem0:mem0 . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R mem0:mem0 /app/logs /app/data

# Switch to non-root user
USER mem0

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default environment variables
ENV MCP_HOST=0.0.0.0 \
    MCP_PORT=8001 \
    MCP_DEBUG=false \
    MEM0_BASE_URL=http://localhost:8000 \
    MEM0_API_VERSION=v1 \
    MCP_LOG_LEVEL=INFO \
    MCP_LOG_TO_FILE=true \
    MCP_LOG_FILE_PATH=/app/logs/server.log

# Start command
CMD ["python", "run_server.py"]