# ── Stage 1: Base ──────────────────────────────────────
FROM node:20-alpine AS base
WORKDIR /app
RUN apk add --no-cache wget

# ── Stage 2: Dependencies ─────────────────────────────
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

# ── Stage 3: Development ──────────────────────────────
FROM base AS development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npx", "nodemon"]

# ── Stage 4: Build ────────────────────────────────────
FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build
RUN npm ci --omit=dev --ignore-scripts

# ── Stage 5: Production ──────────────────────────────
FROM node:20-alpine AS production
RUN apk add --no-cache wget dumb-init
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -g 1001 appgroup && adduser -u 1001 -G appgroup -s /bin/sh -D appuser
COPY --from=build --chown=appuser:appgroup /app/dist ./dist
COPY --from=build --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=build --chown=appuser:appgroup /app/package.json ./
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --spider -q http://localhost:3000/health/liveness || exit 1
CMD ["dumb-init", "node", "dist/server.js"]
