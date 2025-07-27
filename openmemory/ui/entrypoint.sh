#!/bin/sh

# OpenMemory UI Standalone Entrypoint
# This script configures the UI for standalone operation

set -e

echo "🚀 Starting OpenMemory UI in standalone mode..."

# Ensure the working directory is correct
cd /app

# Set default environment variables if not provided
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
export NEXT_PUBLIC_USER_ID="${NEXT_PUBLIC_USER_ID:-standalone-user}"
export NEXT_PUBLIC_ENABLE_MOCKING="${NEXT_PUBLIC_ENABLE_MOCKING:-true}"
export NEXT_PUBLIC_MOCK_OPENMEMORY="${NEXT_PUBLIC_MOCK_OPENMEMORY:-true}"
export NEXT_PUBLIC_MOCK_MEM0="${NEXT_PUBLIC_MOCK_MEM0:-true}"
export NEXT_PUBLIC_STANDALONE_MODE="${NEXT_PUBLIC_STANDALONE_MODE:-true}"

# Log configuration
echo "📋 Configuration:"
echo "  - API URL: ${NEXT_PUBLIC_API_URL}"
echo "  - User ID: ${NEXT_PUBLIC_USER_ID}"
echo "  - Mocking Enabled: ${NEXT_PUBLIC_ENABLE_MOCKING}"
echo "  - Standalone Mode: ${NEXT_PUBLIC_STANDALONE_MODE}"

# Replace environment variables in the built files for runtime configuration
if [ -d ".next" ]; then
    echo "🔧 Configuring runtime environment variables..."

    # Replace env variable placeholders with real values
    printenv | grep NEXT_PUBLIC_ | while read -r line ; do
        key=$(echo "$line" | cut -d "=" -f1)
        value=$(echo "$line" | cut -d "=" -f2-)

        # Escape special characters for sed
        escaped_value=$(echo "$value" | sed 's/[[\.*^$()+?{|]/\\&/g')

        # Replace in JavaScript files
        find .next/ -type f -name "*.js" -exec sed -i "s|$key|$escaped_value|g" {} \;
    done

    echo "✅ Runtime configuration completed"
else
    echo "⚠️  Warning: .next directory not found, skipping runtime configuration"
fi

# Validate that the server file exists
if [ ! -f "server.js" ]; then
    echo "❌ Error: server.js not found. Make sure the application was built correctly."
    exit 1
fi

echo "🎯 Starting Next.js server on port ${PORT:-3000}..."

# Execute the container's main process (CMD in Dockerfile)
exec "$@"