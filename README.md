# hybrid-enterprise-ai-agent-stack

Monorepo scaffold for a **hybrid enterprise AI agent platform** that supports:

- local development on **Windows/WSL2** and **macOS Apple Silicon**
- hardened **Docker Compose** deployment on **Hetzner bare-metal**
- a secondary **Kubernetes ZeroClaw reference deployment**

---

## Canonical Platform Narrative

This repository has **one canonical platform story**:

- **Primary runtime: Docker Compose hybrid stack**  
  The source of truth for the platform is the hybrid Compose topology defined in
  `docker-compose.yml` and `docker-compose.local.yml`.

- **Secondary reference deployment: Kubernetes ZeroClaw assistant**  
  The manifests under `k8s/apps/zeroclaw-assistant/` are a focused reference
  deployment for a ZeroClaw assistant running behind a Cloudflare Tunnel. They
  are not the primary control plane for this repository.

If a file or operational decision appears to conflict with that model, the
Compose-based hybrid stack is the intended default.

---

## Architecture Overview

Release-oriented component map and review checklist: [`docs/architecture.md`](docs/architecture.md).

### Primary runtime: Docker Compose hybrid stack

```
Internet
  │
  ▼
Traefik
  │
  ├── oauth2-proxy (Entra ID ForwardAuth)
  │
  ├── OpenWork (frontend)
  ├── n8n (workflow engine)
  └── internal service routing
        │
        ├── OpenClaw (agent runtime)
        ├── NemoClaw (sandbox)
        ├── MCP n8n bridge
        ├── 1Password Connect
        ├── PostgreSQL
        ├── Qdrant
        └── vLLM / Ollama
```

### Secondary reference deployment: Kubernetes ZeroClaw assistant

```
Internet
  │
  ▼
Cloudflare Edge
  │
  ▼
Cloudflare Tunnel
  │
  ▼
Hetzner Kubernetes
  │
  └── zeroclaw-assistant pod
      ├── zeroclaw
      └── cloudflared
```

---

## Repository Structure

```text
infrastructure/
├── sso/                         # Entra ID / oauth2-proxy configuration
└── traefik/                     # Static + dynamic Traefik configuration

backend/
├── openclaw/                    # Backend source mount point
└── nemoclaw/                    # Sandbox source mount point

frontend/
└── openwork/                    # Frontend source mount point

mcp-servers/
└── n8n-bridge/                  # Python MCP server for n8n + 1Password

k8s/
└── apps/
    └── zeroclaw-assistant/      # Kubernetes reference deployment

docker-compose.yml               # Production hybrid stack
docker-compose.local.yml         # Local development stack
Makefile                         # Standard local/prod orchestration commands
```

---

## Runtime Boundaries

- `docker-compose.yml`  
  Production topology for Hetzner bare-metal with Traefik, Entra ID SSO,
  vLLM, n8n, PostgreSQL, 1Password Connect, Qdrant, OpenClaw, NemoClaw,
  OpenWork, and the MCP bridge.

- `docker-compose.local.yml`  
  Local development topology with:
  - `windows` profile for `vLLM`
  - `mac` profile for `Ollama`
  - bind mounts for `frontend/` and `backend/`
  - local HTTP-only Traefik without SSO

- `k8s/apps/zeroclaw-assistant/`  
  A separate, reference-grade K8s deployment pattern for a Cloudflare Tunnel
  fronted ZeroClaw assistant.

---

## Quick Start

### Local development

`make dev-mac` / `make dev-windows` expect **Bash** (e.g. Git for Windows). They copy `.env.local.example` → `.env.local` when missing and seed `secrets/1password-credentials.json` from the example file so Compose bind mounts succeed (replace that file with a real Connect bundle before using MCP secret tools).

For a **GPU-free** local slice (infra + n8n + MCP bridge only, no agents), use `make dev-core` — intended for smoke tests or constrained hosts, not day-to-day development. See `docs/architecture.md` for profile details.

**n8n** is also bound to **http://127.0.0.1:5678** on the host (in addition to Traefik + `N8N_HOST`) so you can open the UI when the Docker provider for Traefik misbehaves on some Docker Desktop builds.

```bash
cp .env.local.example .env.local
make dev-mac
```

or:

```bash
cp .env.local.example .env.local
make dev-windows
```

### Production

```bash
cp .env.prod.example .env.prod
make prod
```

### Kubernetes reference deployment

```bash
kubectl apply -k k8s/apps/zeroclaw-assistant/
```

---

## MCP control plane

Operational reference for MCP tools, policy bundles, and bridge environment variables: [`docs/mcp-control-plane.md`](docs/mcp-control-plane.md).

---

## Security Posture

- segmented Docker networks across proxy, app, db, and AI tiers
- non-root execution defaults in Compose and Kubernetes
- read-only root filesystems for production services where supported
- ForwardAuth in front of user-facing production services
- placeholder-only secrets in version control

---

## Current Scope Notes

- This repository currently contains **platform scaffolding and integration
  glue**.
- The `backend/openclaw`, `backend/nemoclaw`, and `frontend/openwork`
  directories are currently mount points/placeholders rather than full
  in-repo upstream application sources.

---

## License

This repository is currently **UNLICENSED** unless and until the owner publishes
an explicit license grant in `LICENSE`.
