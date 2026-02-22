# Contributing

Thank you for your interest in contributing to the Cloud-Native MEAN Stack Boilerplate. This guide covers the process for contributing to this project.

## Getting Started

1. Fork the repository and clone your fork.
2. Install dependencies: `npm run install:all`
3. Copy environment files: `cp backend/.env.example backend/.env`
4. Start the development stack: `docker compose up -d` or run services locally.

## Development Workflow

1. Create a feature branch from `main`:

```bash
git checkout -b feat/your-feature-name
```

2. Make your changes, ensuring code quality:

```bash
npm run lint
npm run test
```

3. Commit using **Conventional Commits**:

```bash
git commit -m "feat: add user profile endpoint"
git commit -m "fix: resolve JWT token expiry issue"
git commit -m "docs: update API endpoint table"
```

   Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

4. Push your branch and open a Pull Request against `main`.

## Code Standards

- **TypeScript**: Strict mode enabled. All functions must have explicit type annotations.
- **Linting**: ESLint for backend, Prettier for formatting across both projects.
- **Testing**: Write tests for new features. Backend uses Jest; frontend uses Karma/Jasmine.
- **Commits**: Enforced via Husky + commitlint. Non-conforming commits will be rejected by the pre-commit hook.

## Pull Request Guidelines

- Keep PRs focused on a single change.
- Include a clear description of what changed and why.
- Ensure CI passes (lint, test, build, Docker validation).
- Update documentation if your change affects public APIs or configuration.

## Reporting Issues

- Use GitHub Issues with a clear title and detailed description.
- For security vulnerabilities, see [SECURITY.md](./SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).
