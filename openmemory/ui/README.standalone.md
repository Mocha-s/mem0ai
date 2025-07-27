# OpenMemory UI - Standalone Mode

This document explains how to run the OpenMemory UI as a standalone application using Docker, without requiring any backend services or additional configuration.

## 🚀 Quick Start

### Option 1: Using the Run Script (Recommended)

```bash
# Make the script executable (if not already)
chmod +x run-standalone.sh

# Build and run the UI
./run-standalone.sh run

# Run on a different port
./run-standalone.sh run -p 8080

# Run in detached mode
./run-standalone.sh run -d
```

### Option 2: Using Docker Compose

```bash
# Start the UI
docker-compose -f docker-compose.standalone.yml up

# Start in detached mode
docker-compose -f docker-compose.standalone.yml up -d

# Stop the UI
docker-compose -f docker-compose.standalone.yml down
```

### Option 3: Using Docker Commands

```bash
# Build the image
docker build -t openmemory-ui:standalone .

# Run the container
docker run -p 3000:3000 --name openmemory-ui-standalone openmemory-ui:standalone
```

## 📋 Features in Standalone Mode

- ✅ **Complete UI Experience**: Full OpenMemory interface with all components
- ✅ **Mock API Integration**: Built-in MSW mocks for both OpenMemory and Mem0 APIs
- ✅ **No Backend Required**: Runs completely independently
- ✅ **Demo Data**: Pre-populated with sample memories and data
- ✅ **All Components**: Access to all UI components and features
- ✅ **Responsive Design**: Works on desktop, tablet, and mobile
- ✅ **Dark/Light Mode**: Full theme support
- ✅ **Health Monitoring**: Built-in health check endpoint

## 🔧 Configuration

### Environment Variables

You can customize the standalone mode using environment variables:

```bash
# API Configuration (for future backend integration)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USER_ID=standalone-user

# Mock Configuration
NEXT_PUBLIC_ENABLE_MOCKING=true
NEXT_PUBLIC_MOCK_OPENMEMORY=true
NEXT_PUBLIC_MOCK_MEM0=true

# Standalone Mode
NEXT_PUBLIC_STANDALONE_MODE=true

# Demo Settings
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_SHOW_DEBUG_INFO=false
```

### Using Custom Environment Variables

```bash
# With run script
NEXT_PUBLIC_API_URL=http://my-api.com ./run-standalone.sh run

# With Docker
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://my-api.com \
  -e NEXT_PUBLIC_USER_ID=my-user \
  openmemory-ui:standalone

# With Docker Compose
NEXT_PUBLIC_API_URL=http://my-api.com docker-compose -f docker-compose.standalone.yml up
```

## 🛠️ Available Commands

### Run Script Commands

```bash
# Build and run
./run-standalone.sh run

# Build only
./run-standalone.sh build

# Start existing container
./run-standalone.sh start

# Stop container
./run-standalone.sh stop

# Restart container
./run-standalone.sh restart

# Show logs
./run-standalone.sh logs

# Check health
./run-standalone.sh health

# Open shell in container
./run-standalone.sh shell

# Clean up (remove container and image)
./run-standalone.sh clean

# Show help
./run-standalone.sh --help
```

### Run Script Options

```bash
# Custom port
./run-standalone.sh run -p 8080

# Detached mode
./run-standalone.sh run -d

# Build without cache
./run-standalone.sh build --no-cache

# Combine options
./run-standalone.sh run -p 8080 -d --no-cache
```

## 🏥 Health Check

The standalone UI includes a health check endpoint:

```bash
# Check if the UI is running
curl http://localhost:3000/api/health

# Example response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "uptime": 123.45,
  "environment": "production",
  "version": "1.0.0",
  "standalone": true,
  "mocking": true
}
```

## 📊 Monitoring

### Container Logs

```bash
# Follow logs
./run-standalone.sh logs

# Or with Docker
docker logs -f openmemory-ui-standalone
```

### Container Status

```bash
# Check status
./run-standalone.sh health

# Or with Docker
docker ps -f name=openmemory-ui-standalone
```

## 🔍 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Use a different port
   ./run-standalone.sh run -p 8080
   ```

2. **Container Won't Start**
   ```bash
   # Check logs
   ./run-standalone.sh logs
   
   # Rebuild without cache
   ./run-standalone.sh build --no-cache
   ./run-standalone.sh run
   ```

3. **Health Check Fails**
   ```bash
   # Check if container is running
   docker ps
   
   # Check health endpoint
   curl http://localhost:3000/api/health
   ```

4. **Clean Start**
   ```bash
   # Remove everything and start fresh
   ./run-standalone.sh clean
   ./run-standalone.sh run
   ```

### Debug Mode

Enable debug information:

```bash
NEXT_PUBLIC_SHOW_DEBUG_INFO=true ./run-standalone.sh run
```

## 🌐 Accessing the UI

Once running, access the OpenMemory UI at:

- **Main UI**: http://localhost:3000
- **Health Check**: http://localhost:3000/api/health
- **Storybook** (if built): http://localhost:6006

## 🔗 Integration with Backend

When you're ready to connect to a real backend:

1. **Stop the standalone container**:
   ```bash
   ./run-standalone.sh stop
   ```

2. **Run with backend URL**:
   ```bash
   NEXT_PUBLIC_API_URL=http://your-backend:8000 \
   NEXT_PUBLIC_ENABLE_MOCKING=false \
   ./run-standalone.sh run
   ```

3. **Or update environment variables** in your deployment

## 📦 Production Deployment

For production deployment:

1. **Build the image**:
   ```bash
   docker build -t openmemory-ui:latest .
   ```

2. **Push to registry**:
   ```bash
   docker tag openmemory-ui:latest your-registry/openmemory-ui:latest
   docker push your-registry/openmemory-ui:latest
   ```

3. **Deploy with your orchestration tool** (Kubernetes, Docker Swarm, etc.)

## 🤝 Support

If you encounter any issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Review container logs: `./run-standalone.sh logs`
3. Verify health status: `./run-standalone.sh health`
4. Try a clean restart: `./run-standalone.sh clean && ./run-standalone.sh run`

---

**Note**: This standalone mode is perfect for demos, development, and testing. For production use with real data, connect to the OpenMemory backend services.
