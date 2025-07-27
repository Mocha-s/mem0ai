#!/bin/bash

# OpenMemory UI Standalone Runner
# This script helps you run the OpenMemory UI in standalone mode

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
COMMAND="run"
PORT=3000
BUILD_CACHE="true"
DETACHED="false"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show help
show_help() {
    cat << EOF
OpenMemory UI Standalone Runner

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    run         Build and run the UI container (default)
    build       Build the Docker image only
    start       Start existing container
    stop        Stop running container
    restart     Restart the container
    logs        Show container logs
    clean       Remove container and image
    health      Check container health
    shell       Open shell in running container

Options:
    -p, --port PORT     Port to run on (default: 3000)
    -d, --detached      Run in detached mode
    --no-cache          Build without cache
    -h, --help          Show this help

Environment Variables:
    NEXT_PUBLIC_API_URL         API endpoint URL (default: http://localhost:8000)
    NEXT_PUBLIC_USER_ID         User ID for standalone mode (default: standalone-user)
    NEXT_PUBLIC_DEMO_MODE       Enable demo mode (default: true)

Examples:
    $0 run                      # Build and run on port 3000
    $0 run -p 8080 -d          # Run on port 8080 in detached mode
    $0 build --no-cache        # Build without cache
    $0 logs                     # Show container logs
    $0 clean                    # Clean up everything

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        run|build|start|stop|restart|logs|clean|health|shell)
            COMMAND="$1"
            shift
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -d|--detached)
            DETACHED="true"
            shift
            ;;
        --no-cache)
            BUILD_CACHE="false"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Container and image names
CONTAINER_NAME="openmemory-ui-standalone"
IMAGE_NAME="openmemory-ui:standalone"

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to build the image
build_image() {
    print_status "Building OpenMemory UI Docker image..."
    
    local build_args=""
    if [ "$BUILD_CACHE" = "false" ]; then
        build_args="--no-cache"
    fi
    
    docker build $build_args -t "$IMAGE_NAME" .
    
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to run the container
run_container() {
    print_status "Starting OpenMemory UI container..."
    
    # Stop existing container if running
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_warning "Stopping existing container..."
        docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    fi
    
    # Remove existing container if exists
    if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
        docker rm "$CONTAINER_NAME" > /dev/null 2>&1
    fi
    
    local run_args="-p $PORT:3000 --name $CONTAINER_NAME"
    
    if [ "$DETACHED" = "true" ]; then
        run_args="$run_args -d"
    fi
    
    # Set environment variables
    local env_vars=""
    if [ ! -z "$NEXT_PUBLIC_API_URL" ]; then
        env_vars="$env_vars -e NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL"
    fi
    if [ ! -z "$NEXT_PUBLIC_USER_ID" ]; then
        env_vars="$env_vars -e NEXT_PUBLIC_USER_ID=$NEXT_PUBLIC_USER_ID"
    fi
    if [ ! -z "$NEXT_PUBLIC_DEMO_MODE" ]; then
        env_vars="$env_vars -e NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE"
    fi
    
    docker run $run_args $env_vars "$IMAGE_NAME"
    
    if [ $? -eq 0 ]; then
        print_success "Container started successfully"
        print_status "OpenMemory UI is running at: http://localhost:$PORT"
        
        if [ "$DETACHED" = "true" ]; then
            print_status "Container is running in detached mode"
            print_status "Use '$0 logs' to view logs"
            print_status "Use '$0 stop' to stop the container"
        fi
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_status "Showing container logs (Ctrl+C to exit)..."
        docker logs -f "$CONTAINER_NAME"
    else
        print_error "Container is not running"
        exit 1
    fi
}

# Function to check health
check_health() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_status "Checking container health..."
        
        # Get container IP
        local container_ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CONTAINER_NAME")
        
        # Check health endpoint
        if curl -f "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
            print_success "Container is healthy and responding"
        else
            print_warning "Container is running but health check failed"
        fi
        
        # Show container status
        docker ps -f name="$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        print_error "Container is not running"
        exit 1
    fi
}

# Function to clean up
clean_up() {
    print_status "Cleaning up OpenMemory UI resources..."
    
    # Stop and remove container
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_status "Stopping container..."
        docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    fi
    
    if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
        print_status "Removing container..."
        docker rm "$CONTAINER_NAME" > /dev/null 2>&1
    fi
    
    # Remove image
    if docker images -q "$IMAGE_NAME" | grep -q .; then
        print_status "Removing image..."
        docker rmi "$IMAGE_NAME" > /dev/null 2>&1
    fi
    
    print_success "Cleanup completed"
}

# Function to open shell
open_shell() {
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        print_status "Opening shell in container..."
        docker exec -it "$CONTAINER_NAME" /bin/sh
    else
        print_error "Container is not running"
        exit 1
    fi
}

# Main execution
check_docker

case $COMMAND in
    run)
        build_image
        run_container
        ;;
    build)
        build_image
        ;;
    start)
        if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
            docker start "$CONTAINER_NAME"
            print_success "Container started"
        else
            print_error "Container does not exist. Use 'run' command first."
            exit 1
        fi
        ;;
    stop)
        if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
            docker stop "$CONTAINER_NAME"
            print_success "Container stopped"
        else
            print_warning "Container is not running"
        fi
        ;;
    restart)
        if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
            docker restart "$CONTAINER_NAME"
            print_success "Container restarted"
        else
            print_error "Container does not exist"
            exit 1
        fi
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_up
        ;;
    health)
        check_health
        ;;
    shell)
        open_shell
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
