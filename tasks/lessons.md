# Lessons Learned

## Phase 1

- Treat repository truthfulness as a testable contract. Public documentation
  must match the actual runtime boundary, source ownership, and legal status of
  the repo.
- Protect internal-only services at the application transport boundary, not only
  with network segmentation. The MCP bridge now enforces an explicit bearer
  token and fails closed when the token is missing.
- Production identity policy must be explicit and mandatory. Wildcard Entra
  access defaults are incompatible with a hardened zero-trust posture.
- Repository-controlled production artifacts must use immutable image references
  or explicit digest placeholders. Floating `latest` tags and `imagePullPolicy:
  Always` were removed from production-owned paths.
- CI/security baselines should be codified with contract tests so workflow drift
  is caught locally before it reaches the remote pipeline.

## Phase 2

- Reproducibility needs to be enforced at the install path, not just documented
  in package metadata. Lockfiles only matter if Docker and CI consume them
  directly.
- Integration coverage should test the public entrypoints and CI wiring, not
  only helper functions. Matrix contracts now protect that boundary.
- Observability baselines should provide a collector path even before a full
  LGTM backend is deployed. Grafana Alloy with OTLP ingress and debug exporters
  is a valid first operational step.
- Runtime hardening benefits from layering: process limits in Compose plus
  namespace and network policy controls in Kubernetes.
- Release engineering should publish immutable artifacts and metadata together.
  Container tags alone are insufficient without provenance, SBOM, and a release
  manifest artifact.

## Phase 3

- Advanced governance features land more safely when expressed as declarative
  policy/config files mounted into a small, auditable control-plane service
  rather than scattered across application code.
- Replayability becomes much more valuable once policy, routing, rollout, and
  lifecycle decisions all emit deterministic fingerprints and audit records in a
  shared ledger format.
- Adaptive routing must treat fallback routes differently from primary
  candidates; otherwise governance and canary semantics collapse into ordinary
  priority sorting.
- Privacy lifecycle controls should be designed alongside legal-hold and
  deletion-request paths from the beginning. Retention logic alone is not enough
  for compliance-grade systems.
- Failure automation is safest when it plans deterministic reactions (`retry`,
  `failover`, `degrade`, `halt`) first. Execution of those actions can then be
  delegated later to a more privileged orchestrator.

## Phase 4

- High-vision architecture can still be delivered safely inside a limited repo
  scope by expressing platform capabilities as declarative planning engines
  first, then wiring them through consistent audit/policy/runtime config paths.
- Confidential execution, tenancy, compliance, optimization, and sovereignty are
  easier to reason about when every decision shares the same deterministic
  request fingerprint and audit ledger contract.
- For sensitive systems, “what should happen?” planning is a safer precursor to
  “do it automatically.” This keeps blast radius low while still making Phase 4
  capabilities concrete and testable.

## Phase 5 — Completion report (Documentation & planning consistency)

**Scope delivered**

- Normalized planning-module settings to `*_config_path` on `BridgeSettings`,
  with canonical `BRIDGE_*_CONFIG_PATH` environment variables and legacy
  `BRIDGE_*_FILE_PATH` fallbacks centralized in `planning_config.py` (Docker
  Compose uses nested defaults so older `.env` keys keep working).
- Added [`docs/mcp-control-plane.md`](../docs/mcp-control-plane.md) and
  contract tests so every registered MCP tool, every
  `infrastructure/policy/*.{local,prod}.json` stem, and every planning `BRIDGE_*`
  key in `planning_config.py` stays documented.
- Added [`docs/architecture.md`](../docs/architecture.md) as the **release-ready
  architecture index** (Compose index table, network tiers, security,
  observability, config boundaries, release checklist) plus
  [`tests/test_architecture_index.py`](../tests/test_architecture_index.py) and
  a README pointer under Architecture Overview.

**Telemetry**

- No new OpenTelemetry instrumentation in Phase 5; behavior unchanged.
  Documentation references existing Alloy / OTLP wiring.

**Lessons**

- Treat “documentation drift” like schema drift: contract tests that parse
  `server.py` (MCP tools), glob policy files, and read `planning_config.py`
  catch omissions before release.
- A dedicated `docs/architecture.md` keeps README narrative short while still
  giving reviewers a single checklist-driven index.
- Optional roadmap items are safest to implement with the same test-first
  discipline as code so they do not rot.

---

**Staff Engineer approval:** Phase 5 is complete. There is **no Phase 6** in
`tasks/todo.md` yet. Confirm approval to add a new roadmap phase, or specify the
next phased work to ingest.
