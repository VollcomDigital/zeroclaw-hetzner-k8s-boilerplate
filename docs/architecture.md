# Architecture index

Release-oriented map of this repository’s **hybrid enterprise AI agent** platform. It aligns with the canonical narrative: the runtime source of truth is Docker Compose (`docker-compose.yml` / `docker-compose.local.yml`).

## Purpose

Use this page during **release reviews**, **onboarding**, and **incident triage** to locate components, data boundaries, and operational hooks without spelunking every manifest.

## Runtime topology

### Primary runtime (Docker Compose)

Production traffic enters through reverse proxy and SSO, then fans out to user-facing apps, agents, workflows, and backing services. The production graph is defined in `docker-compose.yml`; local development mirrors it with `docker-compose.local.yml` (bind mounts, HTTP-only edge).

**Local Compose profiles** (pass explicitly; there is no implicit default):

| Profile | Purpose |
|---------|---------|
| `windows` | Full stack on Windows hosts (vLLM + OpenClaw / NemoClaw / OpenWork). Use `make dev-windows`. |
| `mac` | Full stack on Apple Silicon (Ollama + agents). Use `make dev-mac`. |
| `core` | **Optional** GPU-free slice: Traefik, Alloy, Postgres, n8n, MCP bridge, Qdrant, 1Password Connect — for CI validation or smoke tests only (`make dev-core` / `make validate-local-core`). |

## Compose component index

| Logical role | Compose service | Notes |
|--------------|-----------------|--------|
| Edge / routing | `traefik` | TLS termination, routing, dynamic middleware from `infrastructure/traefik/` |
| Identity gate | `sso` | oauth2-proxy + Entra integration (production compose path) |
| Frontend shell | `openwork` | OpenWork mount point |
| Agent runtime | `openclaw` | OpenClaw mount point |
| Browser sidecar stub | `browser` | Minimal HTTP on port 3000 — `coollabsio/openclaw` nginx proxies `/browser/` here; replace with a real browser/VNC sidecar when needed |
| Sandbox | `nemoclaw` | NemoClaw mount point |
| Inference | `vllm` | Production GPU inference (immutable image contract in compose) |
| Workflows | `n8n` | Automation engine and webhooks |
| MCP bridge | `mcp-server-n8n` | MCP + n8n + 1Password; see `mcp-control-plane.md` |
| Secrets sync | `1password-connect-api`, `1password-connect-sync` | 1Password Connect pair |
| Relational DB | `postgres` | Application / workflow persistence |
| Vectors | `qdrant` | Vector store with API key gate |
| Telemetry ingress | `alloy` | Grafana Alloy — OTLP and forwarding baseline |

## Network tiers

Compose segments east-west traffic into labeled networks (see `docker-compose.yml`):

| Tier | Name | Intent |
|------|------|--------|
| Edge / ingress | `proxy-tier` | Traefik, SSO, public HTTP(S) |
| Application | `app-tier` | Agents, workflows, MCP bridge, frontend |
| Data | `db-tier` | PostgreSQL, Qdrant, and data-adjacent services |
| AI acceleration | `ai-tier` | Inference services and GPU-adjacent workloads |

Treat cross-tier connectivity as a **conscious exception**: new dependencies should default to the narrowest tier that still works.

## Security controls

- **ForwardAuth** in production for user-facing UIs behind `traefik`.
- **Non-root** UIDs and hardened defaults where the stack supports them (see also root `README` → Security Posture).
- **Secrets**: real credentials stay out of git; use `.env.prod.example` / `.env.local.example` as templates only.
- **MCP bridge**: bearer gate (`BRIDGE_ACCESS_TOKEN`) and declarative allowlists via `infrastructure/policy/` bundles — details in `mcp-control-plane.md`.

## Observability

- Services export **OpenTelemetry**-compatible traces and metrics where configured.
- **`alloy`** receives OTLP (`OTEL_EXPORTER_OTLP_*` in compose) and forwards toward your LGTM/Prometheus stack.
- MCP bridge emits structured log lines with trace correlation for webhook and secret operations.

## Configuration and policy

| Area | Location |
|------|----------|
| Environment templates | `.env.prod.example`, `.env.local.example` |
| Traefik static/dynamic | `infrastructure/traefik/` |
| SSO | `infrastructure/sso/` |
| MCP / planning JSON bundles | `infrastructure/policy/` |

Policy files are **versioned contracts**: changing a bundle implies coordinated bridge and workflow behavior — bump images or configs together on release.

## Release review checklist

1. Confirm `docker-compose.yml` still uses **immutable** third-party image references where required by repository contract tests.
2. Verify Entra / SSO placeholders are non-wildcard for production (`README` narrative + `infrastructure/sso/`).
3. Reconcile MCP policy deltas: `infrastructure/policy/*.prod.json` matches mounted paths in the `mcp-server-n8n` service.
4. Scan OTel endpoints and Alloy wiring for environment-specific URLs.
5. Keep `README.md` and this architecture index aligned with the Compose-first runtime narrative.

## Related documentation

- [`mcp-control-plane.md`](./mcp-control-plane.md) — MCP tools, policy bundles, `BRIDGE_*` variables.
- Root [`README.md`](../README.md) — canonical platform story, quick start, repository layout.
