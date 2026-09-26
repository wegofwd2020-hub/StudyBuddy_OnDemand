# =============================================================================
# StudyBuddy OnDemand — Web Frontend Dockerfile
# Multi-stage build: deps → builder → runner
# Local dev: source is bind-mounted; image is used for production-style runs.
# =============================================================================

# Stage 1: install dependencies (cached unless package*.json changes)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
# --legacy-peer-deps: npm install (lenient) and npm ci (strict) disagree on
# peer-dep resolution for @swc/helpers (next pins 0.5.15; some peers want
# >=0.5.17 optionally). Without this flag npm ci aborts with a "lock file
# does not satisfy" error even when the lockfile installs cleanly.
RUN npm ci --prefer-offline --legacy-peer-deps

# Stage 2: build the Next.js application
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Disable Next.js telemetry in builds
ENV NEXT_TELEMETRY_DISABLED=1
# NEXT_PUBLIC_* vars are inlined into the client bundle at build time, so they
# must reach this stage as ARGs (then re-exported as ENV) — runtime env on the
# container has no effect once the bundle is baked.
ARG NEXT_PUBLIC_DEMO_MODE=""
ENV NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE
# Build identifier, so a deploy can prove WHICH commit is running (#583).
# #583's own example was a STALE WEB IMAGE, so the web tier needs this as much
# as the API does. Served by app/build-id/route.ts.
ARG NEXT_PUBLIC_BUILD_ID="dev"
ENV NEXT_PUBLIC_BUILD_ID=$NEXT_PUBLIC_BUILD_ID
RUN npm run build

# Stage 3: dev mode runtime — uses npm run dev for fail-open Auth0 middleware
# ⚠️  SECURITY NOTE: This stage runs in development mode with fail-open authentication.
# It is suitable ONLY for local development and demo environments without Auth0 credentials.
# For production: restore production build (npm run build + node server.js) with non-root user.
# See: web/Dockerfile.production for the secure production runtime.
FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
CMD ["npm", "run", "dev"]
