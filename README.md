# zeroclaw-hetzner-k8s-boilerplate

Kubernetes manifests for deploying a **24/7 personal ZeroClaw AI assistant** on a Hetzner Cloud Kubernetes cluster, secured behind a **Cloudflare Tunnel** and routed through an internal **LiteLLM AI Gateway**.

---

## Architecture Overview

```
Internet
  │
  ▼
Cloudflare Edge (TLS termination, Zero Trust)
  │  Cloudflare Tunnel
  ▼
┌──────────────────────────────────────┐
│  Hetzner K8s Cluster                 │
│  ┌────────────────────────────────┐  │
│  │  Pod: zeroclaw-assistant       │  │
│  │  ┌──────────┐ ┌────────────┐  │  │
│  │  │ zeroclaw │ │ cloudflared│  │  │
│  │  │ (Rust)   │ │ (sidecar)  │  │  │
│  │  └────┬─────┘ └────────────┘  │  │
│  └───────┼────────────────────────┘  │
│          │                           │
│          ▼                           │
│  LiteLLM AI Gateway                 │
│  (cost tracking, rate limiting,     │
│   model routing)                    │
└──────────────────────────────────────┘
```

**Key design decisions:**

- **No public ingress.** ZeroClaw never binds to a public IP. All traffic flows through a Cloudflare Tunnel sidecar, which establishes an outbound-only connection to Cloudflare's edge.
- **Aggressive resource limits.** The Rust binary is extremely lightweight (10Mi RAM request, 50Mi limit) making it cheap to run on small Hetzner nodes.
- **AI Gateway routing.** All LLM API calls are proxied through a LiteLLM gateway for centralized cost tracking, rate limiting, and model routing.

---

## Repository Structure

```
k8s/
└── apps/
    └── zeroclaw-assistant/
        ├── kustomization.yaml   # Kustomize entrypoint
        ├── namespace.yaml       # zeroclaw namespace
        ├── deployment.yaml      # ZeroClaw pod (Rust app + cloudflared sidecar)
        ├── configmap.yaml       # Non-sensitive config (gateway URL)
        └── secret.yaml          # Placeholder secrets (tunnel token, API key)
```

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Hetzner K8s cluster** | A running cluster with `kubectl` access configured |
| **Cloudflare Tunnel** | A tunnel created in the [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com/) with a valid token |
| **LiteLLM Gateway** | An accessible LiteLLM proxy instance and a virtual API key |
| **Container image** | The ZeroClaw Rust binary published to a registry (default: `ghcr.io/yourorg/zeroclaw-assistant`) |

---

## Quick Start

### 1. Configure Secrets

Edit `k8s/apps/zeroclaw-assistant/secret.yaml` and replace the placeholder values:

```yaml
stringData:
  cloudflare_tunnel_token: "<your-tunnel-token>"
  litellm_api_key: "<your-virtual-api-key>"
```

> **Production note:** Do not commit real secrets. Use [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets), [External Secrets Operator](https://external-secrets.io/), or inject via CI/CD.

### 2. Configure the Gateway URL

Edit `k8s/apps/zeroclaw-assistant/configmap.yaml` if your LiteLLM gateway URL differs from the default:

```yaml
data:
  litellm_gateway_url: "https://ai-gateway.yourcompany.com"
```

### 3. Update the Container Image

In `k8s/apps/zeroclaw-assistant/deployment.yaml`, replace the image reference with your actual registry path and tag:

```yaml
image: ghcr.io/yourorg/zeroclaw-assistant:v0.1.0
```

### 4. Deploy

```bash
kubectl apply -k k8s/apps/zeroclaw-assistant/
```

### 5. Verify

```bash
kubectl -n zeroclaw get pods
kubectl -n zeroclaw logs deploy/zeroclaw-assistant -c zeroclaw
kubectl -n zeroclaw logs deploy/zeroclaw-assistant -c cloudflared
```

---

## Resource Budget

| Container | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---|---|---|---|---|
| `zeroclaw` | 10m | 100m | 10Mi | 50Mi |
| `cloudflared` | 10m | 50m | 32Mi | 64Mi |
| **Pod total** | **20m** | **150m** | **42Mi** | **114Mi** |

The entire pod fits comfortably on the smallest Hetzner node types (CX11 / CAX11).

---

## Security

- **Zero Trust networking** — No `LoadBalancer` or `NodePort` services. All ingress is via Cloudflare Tunnel.
- **Read-only root filesystem** — Both containers run with `readOnlyRootFilesystem: true`.
- **Non-root execution** — Both containers run as unprivileged users.
- **Capabilities dropped** — All Linux capabilities are dropped.
- **Secret rotation** — Secrets are referenced from a Kubernetes Secret object; rotate by updating the Secret and restarting the pod.

---

## Customization

### Adding more assistants

Duplicate the `k8s/apps/zeroclaw-assistant/` directory, update the names and labels, and add the new directory to your Kustomize overlay or ArgoCD `Application`.

### Scaling

Increase `spec.replicas` in `deployment.yaml`. The Cloudflare Tunnel connector handles load balancing across replicas automatically.

### Monitoring

Add Prometheus annotations to the pod template if your cluster runs a Prometheus stack:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
```

---

## License

See [LICENSE](LICENSE) for details.
