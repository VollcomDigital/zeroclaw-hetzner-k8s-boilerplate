# Cloud-Native MEAN Stack Boilerplate

A modern, production-ready MEAN stack (MongoDB, Express.js, Angular, Node.js) boilerplate built with **TypeScript** and **12-Factor App** methodology.

## Tech Stack

| Layer    | Technology                          |
| -------- | ----------------------------------- |
| Database | MongoDB 7 + Mongoose ODM            |
| Backend  | Node.js 20+ / Express.js            |
| Frontend | Angular 17+ (Standalone, Signals)   |
| Language | TypeScript (strict mode)            |
| Tooling  | ESLint, Prettier, Husky, Commitlint |

## Quick Start

### Prerequisites

- Node.js 20+
- MongoDB (local or Docker)
- npm

### Local Development

```bash
# Clone and install
git clone <repo>
cd cloud-native-mean-boilerplate
npm run install:all

# Backend
cp backend/.env.example backend/.env
npm run backend:dev

# Frontend (new terminal)
npm run frontend:dev
```

- Backend: http://localhost:3000
- Frontend: http://localhost:4200

### Docker Compose

```bash
docker-compose up -d
```

- Backend: http://localhost:3000
- Frontend: http://localhost:4200 (served by Nginx)
- MongoDB: localhost:27017

## Health Endpoints

| Endpoint                       | Purpose                             |
| ------------------------------ | ----------------------------------- |
| `GET /api/v1/health/liveness`  | Process alive (Kubernetes liveness) |
| `GET /api/v1/health/readiness` | Ready to serve (DB connected)       |

## Project Structure

```
├── backend/          # Express + Mongoose
│   └── src/
│       ├── config/   # Zod env validation
│       ├── common/   # Errors, middleware
│       ├── modules/  # health, users, auth
│       ├── db/       # Mongoose connection
│       └── logger/   # Pino
├── frontend/         # Angular 17+
│   └── src/app/
│       ├── core/     # Interceptors, guards, services
│       └── features/  # home, auth, users
├── .github/workflows/ci.yml
├── docker-compose.yml
└── .env.example
```

## Scripts

| Script                  | Description              |
| ----------------------- | ------------------------ |
| `npm run dev`           | Start backend + frontend |
| `npm run backend:dev`   | Backend with tsx watch   |
| `npm run frontend:dev`  | Angular dev server       |
| `npm run backend:test`  | Jest tests               |
| `npm run frontend:test` | Karma/Jasmine tests      |
| `npm run lint`          | ESLint                   |
| `npm run format:check`  | Prettier check           |

## Environment Variables

Copy `.env.example` to `.env` and configure. Backend validates config at startup (Zod).

## Commit Convention

Uses [Conventional Commits](https://www.conventionalcommits.org/) via Husky + Commitlint:

```
feat: add user registration
fix: correct health check status code
docs: update README
```

## License

MIT
