# frontend/Dockerfile
# Multi-stage Next.js production build with standalone output

# ── Stage 1: Deps ─────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# Install dependencies (ci for reproducible installs)
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline


# ── Stage 2: Builder ──────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build-time env — NEXT_PUBLIC_* vars must be available at build time
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Enable Next.js standalone output for minimal container image
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# ── Stage 3: Runtime ──────────────────────────────────────
FROM node:20-alpine AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Add non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy only the output needed to run the app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
