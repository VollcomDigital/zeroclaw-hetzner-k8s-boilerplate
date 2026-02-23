# ── Stage 1: Base ──────────────────────────────────────
FROM node:25-alpine AS base
WORKDIR /app

# ── Stage 2: Dependencies ─────────────────────────────
FROM base AS deps
COPY package.json package-lock.json* ./
RUN npm ci

# ── Stage 3: Development ──────────────────────────────
FROM base AS development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 4200
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--poll", "2000"]

# ── Stage 4: Build ────────────────────────────────────
FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npx ng build --configuration=production

# ── Stage 5: Production (Nginx) ──────────────────────
FROM nginx:1.27-alpine AS production
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --spider -q http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
