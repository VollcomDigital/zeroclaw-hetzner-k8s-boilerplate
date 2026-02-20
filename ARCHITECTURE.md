# MEAN Stack Cloud-Native Boilerplate — Directory Structure

## Proposed Structure (Two-Folder Layout)

```
/
├── .github/
│   └── workflows/
│       └── ci.yml                    # Lint, test, build workflow
├── .husky/
│   ├── pre-commit                    # Lint-staged hook
│   └── commit-msg                    # Commitlint validation
├── backend/                          # Node.js + Express + Mongoose
│   ├── src/
│   │   ├── config/
│   │   │   ├── index.ts              # Zod-validated env config
│   │   │   └── env.schema.ts
│   │   ├── common/
│   │   │   ├── errors/
│   │   │   │   ├── AppError.ts
│   │   │   │   └── errorHandler.ts
│   │   │   ├── middleware/
│   │   │   │   ├── errorHandler.ts
│   │   │   │   ├── notFound.ts
│   │   │   │   └── requestLogger.ts
│   │   │   └── utils/
│   │   │       └── response.ts
│   │   ├── modules/
│   │   │   ├── health/
│   │   │   │   ├── health.controller.ts
│   │   │   │   ├── health.router.ts
│   │   │   │   └── health.service.ts
│   │   │   ├── users/
│   │   │   │   ├── user.model.ts
│   │   │   │   ├── user.controller.ts
│   │   │   │   ├── user.router.ts
│   │   │   │   └── user.service.ts
│   │   │   └── auth/
│   │   │       ├── auth.controller.ts
│   │   │       ├── auth.router.ts
│   │   │       └── auth.service.ts
│   │   ├── db/
│   │   │   └── mongoose.ts
│   │   ├── logger/
│   │   │   └── index.ts              # Pino logger
│   │   ├── app.ts
│   │   └── server.ts
│   ├── tests/
│   │   ├── setup.ts
│   │   ├── health.test.ts
│   │   └── users/
│   │       └── user.service.test.ts
│   ├── .env.example
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   └── jest.config.js
├── frontend/                         # Angular 17+ Standalone + Signals
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   ├── interceptors/
│   │   │   │   │   ├── auth.interceptor.ts
│   │   │   │   │   └── error.interceptor.ts
│   │   │   │   ├── guards/
│   │   │   │   │   └── auth.guard.ts
│   │   │   │   ├── services/
│   │   │   │   │   └── api.service.ts
│   │   │   │   └── core.module.ts (minimal, for DI)
│   │   │   ├── shared/
│   │   │   │   ├── components/
│   │   │   │   │   ├── layout/
│   │   │   │   │   └── ui/
│   │   │   │   └── models/
│   │   │   ├── features/
│   │   │   │   ├── home/
│   │   │   │   ├── auth/
│   │   │   │   └── users/
│   │   │   └── app.config.ts
│   │   ├── index.html
│   │   └── main.ts
│   ├── .env.example
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── angular.json
│   ├── package.json
│   └── tsconfig.json
├── .env.example                      # Root composite example
├── .eslintrc.cjs
├── .prettierrc
├── .lintstagedrc.cjs
├── commitlint.config.cjs
├── docker-compose.yml
├── package.json                     # Root workspace/scripts
├── tsconfig.base.json
└── README.md
```

## Module Responsibilities

| Path                        | Purpose                                     |
| --------------------------- | ------------------------------------------- |
| `backend/src/config`        | Environment validation (Zod), app config    |
| `backend/src/common`        | Shared errors, middleware, response utils   |
| `backend/src/modules/*`     | Domain-driven modules (health, users, auth) |
| `backend/src/db`            | Mongoose connection, retry logic            |
| `backend/src/logger`        | Pino structured logging                     |
| `frontend/src/app/core`     | Interceptors, guards, shared services       |
| `frontend/src/app/features` | Lazy-loaded feature modules                 |

## 12-Factor Compliance

- **I. Codebase** — Single repo, two deployable units (frontend/backend)
- **II. Dependencies** — Explicit `package.json` per app
- **III. Config** — `.env` + Zod validation, no hardcoded secrets
- **IV. Backing services** — MongoDB as attached resource, URI from env
- **V. Build/release/run** — Docker multi-stage, separate build & run
- **VI. Processes** — Stateless backend, frontend served by Nginx
- **VII. Port binding** — Express binds to `PORT`, Nginx to 80
- **VIII. Concurrency** — Horizontal scaling via processes
- **IX. Disposability** — Graceful shutdown, health checks
- **X. Dev/prod parity** — Same stack in Docker Compose
- **XI. Logs** — Structured JSON (Pino) to stdout
- **XII. Admin processes** — Migrations/scripts as separate commands
