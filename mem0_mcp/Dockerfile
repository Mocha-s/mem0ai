# Multi-stage build for Mem0 MCP Server
FROM python:3.11-slim as builder

# Set build-time environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src"

# Create non-root user
RUN groupadd --gid 1000 mem0 && \
    useradd --uid 1000 --gid mem0 --shell /bin/bash --create-home mem0

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create app directory and set ownership
RUN mkdir -p /app && chown -R mem0:mem0 /app
WORKDIR /app

# Copy application code
COPY --chown=mem0:mem0 . .

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data && \
    chown -R mem0:mem0 /app/logs /app/data

# Switch to non-root user
USER mem0

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default configuration
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