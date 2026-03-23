# MCP control plane (n8n-bridge)

The `mcp-servers/n8n-bridge` service exposes MCP tools that integrate **n8n webhooks**, **1Password Connect**, **model routing**, and **declarative planning** modules. Policy JSON under `infrastructure/policy/` is mounted into the container and wired through `BridgeSettings` / environment variables (see below).

## MCP tools

| Tool | Role |
|------|------|
| `trigger_n8n_workflow` | POST to an allowed n8n webhook with idempotency and audit metadata. |
| `get_1password_secret` | Read secret inventory or a specific field via 1Password Connect. |
| `select_model_route` | Choose a model route from the routing config under data-classification, latency, and optional `estimated_total_tokens` / `max_cost_usd` governance. |
| `plan_vector_memory_lifecycle` | Plan retention / expiry actions for vector memory segments from policy. |
| `plan_progressive_rollout` | Plan progressive rollout (workflows / prompts) from rollout config. |
| `plan_failure_mode` | Plan deterministic failure reactions (retry, degrade, halt, etc.). |
| `plan_confidential_execution` | Plan confidential execution targets (attestation, GPU, regions). |
| `plan_agent_control_plane` | Plan agent tenancy, quotas, and policy packs from control-plane config. |
| `plan_compliance_case` | Plan compliance workflows (evidence bundles, erasure targets). |
| `plan_autonomous_optimization` | Plan optimization deltas against routing cost/latency signals. |
| `plan_sovereignty_mode` | Plan data-sovereignty mode and allowed regions from sovereignty rules. |

All planning tools are **read-only planners**: they load JSON policy, compute a structured plan, and emit audit-friendly fingerprints; they do not mutate external systems.

## Policy bundles

Production and local stacks each mount a pair of JSON files per concern. Source paths in the repository:

| Concern | Local | Production |
|---------|--------|------------|
| MCP tool / webhook / secret allowlists | `infrastructure/policy/mcp-policy.local.json` | `infrastructure/policy/mcp-policy.prod.json` |
| Model routing | `infrastructure/policy/model-routing.local.json` | `infrastructure/policy/model-routing.prod.json` |
| Vector memory lifecycle | `infrastructure/policy/vector-memory.local.json` | `infrastructure/policy/vector-memory.prod.json` |
| Progressive rollout | `infrastructure/policy/rollout.local.json` | `infrastructure/policy/rollout.prod.json` |
| Failure modes | `infrastructure/policy/failure-mode.local.json` | `infrastructure/policy/failure-mode.prod.json` |
| Confidential execution | `infrastructure/policy/confidential-execution.local.json` | `infrastructure/policy/confidential-execution.prod.json` |
| Agent control plane | `infrastructure/policy/agent-control-plane.local.json` | `infrastructure/policy/agent-control-plane.prod.json` |
| Compliance platform | `infrastructure/policy/compliance-platform.local.json` | `infrastructure/policy/compliance-platform.prod.json` |
| Autonomous optimization | `infrastructure/policy/autonomous-optimization.local.json` | `infrastructure/policy/autonomous-optimization.prod.json` |
| Sovereignty | `infrastructure/policy/sovereignty.local.json` | `infrastructure/policy/sovereignty.prod.json` |

Compose maps these files to the paths expected by the bridge (see `docker-compose.yml` / `docker-compose.local.yml`).

## Bridge environment: planning config paths

Canonical variables use the `*_CONFIG_PATH` suffix. Older `*_FILE_PATH` names are still accepted when the canonical variable is unset or blank (see `planning_config.py`).

| Canonical | Legacy fallback |
|-----------|-----------------|
| `BRIDGE_MCP_POLICY_CONFIG_PATH` | `BRIDGE_POLICY_FILE_PATH` |
| `BRIDGE_MODEL_ROUTING_CONFIG_PATH` | `BRIDGE_ROUTING_FILE_PATH` |
| `BRIDGE_VECTOR_MEMORY_CONFIG_PATH` | `BRIDGE_VECTOR_MEMORY_POLICY_FILE_PATH` |
| `BRIDGE_PROGRESSIVE_ROLLOUT_CONFIG_PATH` | `BRIDGE_ROLLOUT_FILE_PATH` |
| `BRIDGE_FAILURE_MODE_CONFIG_PATH` | `BRIDGE_FAILURE_MODE_FILE_PATH` |
| `BRIDGE_CONFIDENTIAL_EXECUTION_CONFIG_PATH` | `BRIDGE_CONFIDENTIAL_EXECUTION_FILE_PATH` |
| `BRIDGE_AGENT_CONTROL_PLANE_CONFIG_PATH` | `BRIDGE_AGENT_CONTROL_PLANE_FILE_PATH` |
| `BRIDGE_COMPLIANCE_PLATFORM_CONFIG_PATH` | `BRIDGE_COMPLIANCE_PLATFORM_FILE_PATH` |
| `BRIDGE_AUTONOMOUS_OPTIMIZATION_CONFIG_PATH` | `BRIDGE_AUTONOMOUS_OPTIMIZATION_FILE_PATH` |
| `BRIDGE_SOVEREIGNTY_CONFIG_PATH` | `BRIDGE_SOVEREIGNTY_FILE_PATH` |

Examples for local and production stacks live in `.env.local.example` and `.env.prod.example`.

## Related runtime variables

- `BRIDGE_ACCESS_TOKEN` — bearer token checked by the bridge HTTP layer.
- `BRIDGE_AUDIT_LEDGER_PATH` — append-only JSONL audit ledger path (not a planning bundle).

## Operational notes

- Planning modules are cached by absolute config path; change files with care in long‑running processes.
- Tool execution for n8n and 1Password is additionally gated by `mcp-policy.*.json` when configured.
