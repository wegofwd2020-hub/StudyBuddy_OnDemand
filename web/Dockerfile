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
RUN npm run build

# Stage 3: minimal production runtime
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Run as non-root
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

# Copy built output
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
