# syntax=docker.io/docker/dockerfile:1

# OpenMemory UI - Standalone Docker Configuration
# This Dockerfile creates a self-contained UI application that can run independently

# Base stage for common setup
FROM node:18-alpine AS base

# Install dependencies for pnpm and add necessary packages
RUN apk add --no-cache \
    libc6-compat \
    curl \
    wget \
    dumb-init \
    && corepack enable \
    && corepack prepare pnpm@latest --activate

WORKDIR /app

# Dependencies stage - install only production dependencies
FROM base AS deps

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies with optimizations for production
# Use --no-frozen-lockfile to handle lockfile sync issues
RUN pnpm install --no-frozen-lockfile --prod=false

# Builder stage - build the application
FROM base AS builder
WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/pnpm-lock.yaml ./pnpm-lock.yaml

# Copy source code
COPY . .

# Create production environment configuration
RUN cp next.config.dev.mjs next.config.mjs

# Create default environment file with standalone configuration
RUN echo "# OpenMemory UI Standalone Configuration" > .env.local && \
    echo "NODE_ENV=production" >> .env.local && \
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env.local && \
    echo "NEXT_PUBLIC_USER_ID=standalone-user" >> .env.local && \
    echo "NEXT_PUBLIC_ENABLE_MOCKING=true" >> .env.local && \
    echo "NEXT_PUBLIC_MOCK_OPENMEMORY=true" >> .env.local && \
    echo "NEXT_PUBLIC_MOCK_MEM0=true" >> .env.local && \
    echo "NEXT_PUBLIC_STANDALONE_MODE=true" >> .env.local

# Build the application
RUN pnpm build

# Production stage - create minimal runtime image
FROM base AS runner
WORKDIR /app

# Set production environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy and setup entrypoint script
COPY --chown=nextjs:nodejs entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Set default environment variables
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check (using wget which is available in alpine)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["/usr/bin/dumb-init", "--", "/app/entrypoint.sh"]
CMD ["node", "server.js"]
