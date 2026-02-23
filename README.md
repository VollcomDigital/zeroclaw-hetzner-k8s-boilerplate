# Cloud-Native MEAN Stack Boilerplate

Production-ready **MongoDB + Express + Angular + Node.js** boilerplate built with **TypeScript**, **Docker**, and the **12-Factor App** methodology.

## Tech Stack

| Layer      | Technology                                      |
|------------|--------------------------------------------------|
| Database   | MongoDB 7 + Mongoose ODM                        |
| Backend    | Node.js 20+, Express 4, TypeScript (strict)     |
| Frontend   | Angular 19, Standalone Components, Signals, SCSS |
| Auth       | JWT + HttpOnly cookie session + bcryptjs         |
| Validation | Zod (backend), Angular Forms (frontend)          |
| Logging    | Pino (structured JSON logging)                   |
| Testing    | Jest (backend), Karma/Jasmine (frontend)         |
| DevOps     | Docker, Docker Compose, GitHub Actions           |

## Project Structure

```
.
├── .github/workflows/ci.yml     # CI pipeline (lint, test, build, Docker)
├── .husky/                       # Git hooks (pre-commit, commit-msg)
├── backend/
│   ├── src/
│   │   ├── config/               # Env validation (Zod), DB connection
│   │   ├── core/
│   │   │   ├── errors/           # Custom error classes (AppError)
│   │   │   ├── logger/           # Pino structured logger
│   │   │   └── middleware/       # Security, error handler, request logger
│   │   ├── modules/
│   │   │   ├── auth/             # JWT auth (register, login, middleware)
│   │   │   ├── health/           # Liveness + Readiness probes
│   │   │   └── users/            # User CRUD (model, service, controller)
│   │   └── shared/               # Response types, async handler utility
│   ├── tests/                    # Unit + integration tests
│   ├── Dockerfile                # Multi-stage (dev + production)
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/             # Auth service, interceptor, guards
│   │   │   ├── features/         # Home, Auth (Login/Register), Dashboard
│   │   │   └── shared/           # Header, Footer, Loading components
│   │   └── environments/         # Dev + production environment configs
│   ├── nginx/nginx.conf          # Production Nginx with SPA fallback
│   ├── Dockerfile                # Multi-stage (dev + Nginx production)
│   └── .env.example
├── docker-compose.yml            # Full stack orchestration
├── .prettierrc                   # Shared Prettier config
├── .commitlintrc.json            # Conventional commits enforcement
└── .lintstagedrc.json            # Lint-staged config
```

## Quick Start

### Prerequisites

- Node.js >= 20
- npm >= 10
- Docker & Docker Compose (for containerized development)

### Option 1: Docker Compose (Recommended)

```bash
# Configure required Docker secrets
cp .env.example .env

# Clone and start the full stack
docker compose up -d

# Backend API:   http://localhost:3000
# Frontend App:  http://localhost:4200
# MongoDB:       localhost:27017
```

### Option 2: Local Development

```bash
# Install all dependencies
npm run install:all

# Copy environment files
cp backend/.env.example backend/.env

# Start backend (requires MongoDB running locally)
npm run dev:backend

# Start frontend (in another terminal)
npm run dev:frontend
```

## API Endpoints

### Health Checks (Kubernetes-ready)

| Method | Endpoint              | Description            |
|--------|-----------------------|------------------------|
| GET    | `/health/liveness`    | Process alive check    |
| GET    | `/health/readiness`   | Service ready check    |

### Authentication

| Method | Endpoint              | Description            |
|--------|-----------------------|------------------------|
| POST   | `/api/v1/auth/register` | Register new user    |
| POST   | `/api/v1/auth/login`    | Login (sets HttpOnly auth cookie)  |
| GET    | `/api/v1/auth/me`       | Get current user     |
| POST   | `/api/v1/auth/logout`   | Clear auth session cookie |

### Users (Protected)

| Method | Endpoint              | Description            |
|--------|-----------------------|------------------------|
| GET    | `/api/v1/users`         | List users (admin only, paginated) |
| GET    | `/api/v1/users/:id`     | Get own user (or admin any user)   |
| PUT    | `/api/v1/users/:id`     | Update own user (or admin any user) |
| DELETE | `/api/v1/users/:id`     | Soft-delete own user (or admin any user) |

### Response Format

All endpoints return a consistent JSON structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

## Environment Variables

All backend configuration is validated at startup using **Zod**. See `backend/.env.example`:

| Variable       | Required | Default              | Description                |
|---------------|----------|----------------------|----------------------------|
| `NODE_ENV`    | No       | `development`        | Runtime environment        |
| `PORT`        | No       | `3000`               | Server port                |
| `MONGODB_URI` | Yes      | —                    | MongoDB connection string  |
| `JWT_SECRET`  | Yes      | —                    | JWT signing secret (min 16 chars) |
| `JWT_EXPIRES_IN` | No       | `7d`                 | Token expiration           |
| `CORS_ORIGIN` | No       | `http://localhost:4200` | Allowed CORS origin     |
| `LOG_LEVEL`   | No       | `info`               | Pino log level             |

## Testing

```bash
# Backend tests (Jest)
npm run test:backend

# Frontend tests (Karma)
npm run test:frontend

# Run all tests
npm run test
```

## Scripts

| Script               | Description                                  |
|---------------------|----------------------------------------------|
| `npm run dev:backend`  | Start backend in development mode           |
| `npm run dev:frontend` | Start Angular dev server                    |
| `npm run build`        | Build both backend and frontend             |
| `npm run test`         | Run all tests                               |
| `npm run lint`         | Lint both projects                          |
| `npm run docker:up`    | Start Docker Compose stack                  |
| `npm run docker:down`  | Stop Docker Compose stack                   |

## Architecture Decisions

- **12-Factor App**: Config via env vars, stateless processes, port binding, dev/prod parity
- **Domain-Driven Modules**: Each feature (auth, users, health) is self-contained
- **Standalone Components**: No NgModules — Angular 21 standalone architecture throughout
- **Signals**: Modern reactive state management in Angular services
- **Lazy Loading**: All feature routes are code-split and lazy-loaded
- **Structured Logging**: JSON logs via Pino for cloud-native log aggregation
- **Health Probes**: Kubernetes-compatible liveness and readiness endpoints
- **Security**: Helmet, CORS, auth-specific + global rate limiting, RBAC, ownership checks, bcrypt password hashing, HttpOnly cookie auth
- **Conventional Commits**: Enforced via Husky + commitlint

## License

MIT
