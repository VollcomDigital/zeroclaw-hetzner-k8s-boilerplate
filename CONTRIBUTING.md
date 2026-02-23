# Contributing

Thanks for contributing to this project.

## Development Setup

1. Install dependencies from the repository root:

```bash
npm install
npm install --prefix backend
npm install --prefix frontend
```

Optional shorthand:

```bash
npm run install:all
```

2. Configure environment files:

```bash
cp backend/.env.example backend/.env
```

3. Run services locally:

```bash
npm run dev:backend
npm run dev:frontend
```

## Branching and Commits

- Use focused branches per feature or fix.
- Follow Conventional Commits:
  - `feat: ...`
  - `fix: ...`
  - `chore: ...`
  - `perf: ...`

## Code Quality Standards

- Backend: TypeScript strict mode and ESLint.
- Frontend: Angular ESLint and Angular template lint rules.
- Run checks before opening a pull request:

```bash
npm run lint
npm run test
npm run build
```

## Pull Request Checklist

- Add tests for behavior changes.
- Update documentation when APIs/configuration changes.
- Ensure CI and security workflows pass.

## Security Reports

For security issues, do not open a public issue. Follow `SECURITY.md`.
