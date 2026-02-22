# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | :white_check_mark: |

## Reporting a Vulnerability

We take the security of this project seriously. If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. Email the maintainers at **security@vollcom-digital.com** with the details.
2. Include a description of the vulnerability, steps to reproduce, and any potential impact.
3. Allow up to **72 hours** for an initial response.

### What to Expect

- **Acknowledgement**: Within 72 hours of your report.
- **Assessment**: We will evaluate the severity and impact within 5 business days.
- **Resolution**: Critical vulnerabilities will be patched as soon as possible. A coordinated disclosure timeline will be agreed upon.
- **Credit**: With your permission, we will credit you in the release notes.

## Security Measures in This Project

- **Helmet.js** for HTTP security headers
- **CORS** configuration with explicit origin allowlisting
- **Rate limiting** to mitigate brute-force and DDoS attacks
- **bcryptjs** for password hashing (no plaintext storage)
- **JWT** authentication with configurable expiry and minimum 16-character secrets
- **Zod** schema validation for all environment variables and API inputs
- **Non-root Docker user** in production containers
- **Multi-stage Docker builds** to minimize production image attack surface

## Best Practices for Deployers

- Never use default credentials in production; always set `JWT_SECRET`, `MONGO_ROOT_PASSWORD`, and other secrets via environment variables.
- Enable MongoDB authentication and network restrictions in production.
- Use TLS/HTTPS termination in front of the application (e.g., via a reverse proxy or load balancer).
- Regularly update dependencies and monitor Dependabot alerts.
- Enable GitHub Advanced Security features (CodeQL, secret scanning) on your repository.
