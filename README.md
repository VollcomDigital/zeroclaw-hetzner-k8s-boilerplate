# zeroclaw-hetzner-k8s-boilerplate

This repository deploys a 24/7 personal ZeroClaw AI assistant to a Hetzner Kubernetes cluster.

The assistant is intentionally lightweight (Rust binary) and is secured by design:

- The assistant pod is not exposed directly to public networks.
- Access is routed through a Cloudflare Tunnel (`cloudflared` sidecar).
- Upstream model traffic is routed through the internal LiteLLM AI Gateway.

## What is included

`k8s/apps/zeroclaw-assistant/` contains the Kubernetes manifests for a single assistant deployment:

- `namespace.yaml`: Dedicated namespace for the assistant.
- `deployment.yaml`: ZeroClaw container + Cloudflared sidecar.
- `configmap.yaml`: Non-secret runtime config (including AI Gateway URL).
- `secret.yaml`: Placeholder secrets for developer virtual API key and tunnel token.
- `kustomization.yaml`: Convenience entrypoint for `kubectl apply -k`.

## Security and networking model

This repo uses a sidecar tunnel pattern:

1. `zeroclaw-assistant` binds inside the pod only (default `127.0.0.1:8080`).
2. `cloudflared` authenticates with `CLOUDFLARE_TUNNEL_TOKEN`.
3. Cloudflare Tunnel forwards allowed traffic to the assistant.

No Kubernetes `Service`, `Ingress`, or `LoadBalancer` is required for public exposure.

## Configuration

### ConfigMap (`configmap.yaml`)

- `LITELLM_GATEWAY_URL`: `https://ai-gateway.yourcompany.com`
- `ZEROCLAW_BIND_ADDRESS`: `127.0.0.1:8080`
- `RUST_LOG`: `info`

### Secret (`secret.yaml`)

Replace placeholder values before production use:

- `DEVELOPER_VIRTUAL_API_KEY`
- `CLOUDFLARE_TUNNEL_TOKEN`

For production, replace the placeholder `Secret` with your preferred sealed/encrypted secret workflow.

## Resource profile

The assistant container is configured for aggressive low-memory operation:

- Requests: `10Mi` memory
- Limits: `50Mi` memory

This matches the expected lightweight Rust runtime footprint.

## Deploy

From repository root:

```bash
kubectl apply -k k8s/apps/zeroclaw-assistant
```

## Operational notes

- Ensure the Cloudflare Tunnel is preconfigured to route to `http://127.0.0.1:8080` inside the pod.
- Replace `ghcr.io/vollcomdigital/zeroclaw-assistant:latest` in `deployment.yaml` with your pinned image tag for stable rollouts.