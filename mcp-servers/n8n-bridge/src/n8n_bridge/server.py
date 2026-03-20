from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
import uvicorn

from n8n_bridge.planning_config import PLANNING_CONFIG_BINDINGS, first_non_empty_env

type JSONPrimitive = str | int | float | bool | None
type JSONValue = JSONPrimitive | dict[str, "JSONValue"] | list["JSONValue"]

LOGGER = logging.getLogger("n8n_bridge")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "mcp-server-n8n")
TRACER = trace.get_tracer(SERVICE_NAME)
MCP_SERVER = FastMCP("n8n-bridge", json_response=True)


class BridgeSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    n8n_base_url: str = "http://n8n:5678"
    op_connect_url: str = "http://1password-connect-api:8080"
    op_connect_token: str | None = None
    bridge_access_token: str | None = None
    audit_ledger_path: str = "/tmp/n8n-bridge/audit-ledger.jsonl"
    mcp_policy_config_path: str | None = None
    model_routing_config_path: str | None = None
    vector_memory_config_path: str | None = None
    progressive_rollout_config_path: str | None = None
    failure_mode_config_path: str | None = None
    confidential_execution_config_path: str | None = None
    agent_control_plane_config_path: str | None = None
    compliance_platform_config_path: str | None = None
    autonomous_optimization_config_path: str | None = None
    sovereignty_config_path: str | None = None
    request_timeout_seconds: float = Field(default=15.0, gt=0)
    idempotency_ttl_seconds: float = Field(default=300.0, ge=0)

    @field_validator("n8n_base_url", "op_connect_url", mode="before")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


class TriggerWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    webhook_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    payload: dict[str, JSONValue] = Field(default_factory=dict)


class SecretRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vault_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    field_label: str | None = Field(default=None, min_length=1)


class ModelRoutingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workload_kind: str = Field(min_length=1)
    data_classification: str = Field(min_length=1)
    max_latency_ms: int = Field(ge=1)
    estimated_total_tokens: int = Field(default=0, ge=0)
    max_cost_usd: float | None = Field(default=None, ge=0)
    require_local: bool = False
    preferred_region: str | None = None


class ModelRouteConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_url: str
    model: str
    provider: str
    capabilities: list[str] = Field(default_factory=list)
    allowed_data_classifications: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=lambda: ["*"])
    max_latency_ms: int = Field(ge=1)
    priority: int = Field(default=100, ge=0)
    requires_local: bool = False
    healthy: bool = True
    current_gpu_utilization_percent: int = Field(default=0, ge=0, le=100)
    max_gpu_utilization_percent: int = Field(default=100, ge=0, le=100)
    current_concurrent_requests: int = Field(default=0, ge=0)
    max_concurrent_requests: int | None = Field(default=None, ge=1)
    estimated_cost_per_1k_tokens_usd: float = Field(default=0.0, ge=0)
    daily_budget_usd: float | None = Field(default=None, ge=0)
    current_spend_usd: float = Field(default=0.0, ge=0)


class ModelRoutingConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    default_route: str | None = None
    routes: dict[str, ModelRouteConfig] = Field(default_factory=dict)


class VectorMemoryLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    data_classification: str = Field(min_length=1)
    pii_labels: list[str] = Field(default_factory=list)
    created_at: datetime
    last_accessed_at: datetime | None = None
    evaluation_time: datetime | None = None
    legal_hold: bool = False
    deletion_requested: bool = False


class VectorMemoryRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    retention_days: int = Field(ge=0)
    expiry_action: str = "delete"


class VectorMemoryPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    default_action: str = "retain"
    classification_rules: dict[str, VectorMemoryRule] = Field(default_factory=dict)
    pii_overrides: dict[str, VectorMemoryRule] = Field(default_factory=dict)


class ProgressiveRolloutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rollout_kind: str = Field(min_length=1)
    rollout_key: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)


class ProgressiveRolloutEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: str
    primary_webhook_id: str | None = None
    shadow_webhook_id: str | None = None
    canary_webhook_id: str | None = None
    active_prompt_version: str | None = None
    canary_prompt_version: str | None = None
    canary_percentage: int = Field(default=0, ge=0, le=100)


class ProgressiveRolloutConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    workflows: dict[str, ProgressiveRolloutEntry] = Field(default_factory=dict)
    prompts: dict[str, ProgressiveRolloutEntry] = Field(default_factory=dict)


class FailureModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str = Field(min_length=1)
    failure_type: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    retry_count: int = Field(default=0, ge=0)
    data_classification: str = Field(min_length=1)


class FailureModeRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: str
    max_retries: int = Field(default=0, ge=0)
    backoff_seconds: list[int] = Field(default_factory=list)
    fallback_target: str | None = None


class FailureModeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    default_action: str = "degrade"
    rules: dict[str, FailureModeRule] = Field(default_factory=dict)


class ConfidentialExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workload_kind: str = Field(min_length=1)
    data_classification: str = Field(min_length=1)
    requires_attestation: bool = False
    requires_gpu: bool = False
    requires_workload_identity: bool = False
    preferred_region: str | None = None


class ConfidentialExecutionTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    execution_mode: str
    provider: str
    endpoint: str
    attested: bool = False
    supports_gpu: bool = False
    provides_workload_identity: bool = False
    allowed_data_classifications: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=lambda: ["*"])
    priority: int = Field(default=100, ge=0)
    healthy: bool = True


class ConfidentialExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    targets: dict[str, ConfidentialExecutionTarget] = Field(default_factory=dict)


class AgentQuotaClass(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_requests_per_minute: int = Field(ge=1)
    max_parallel_tasks: int = Field(ge=1)


class AgentTenantConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    allowed_capabilities: list[str] = Field(default_factory=list)
    allowed_policy_packs: list[str] = Field(default_factory=list)
    default_policy_pack: str
    default_quota_class: str
    workspace_prefix: str


class AgentControlPlaneConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    quota_classes: dict[str, AgentQuotaClass] = Field(default_factory=dict)
    tenants: dict[str, AgentTenantConfig] = Field(default_factory=dict)


class AgentControlPlaneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    requested_capabilities: list[str] = Field(default_factory=list)
    requested_policy_pack: str | None = None
    requested_quota_class: str | None = None


class ComplianceCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regulation: str = Field(min_length=1)
    case_type: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    systems_affected: list[str] = Field(default_factory=list)
    data_classification: str = Field(min_length=1)
    legal_hold: bool = False

    @field_validator("systems_affected")
    @classmethod
    def normalize_systems_affected(cls, value: list[str]) -> list[str]:
        return sorted(dict.fromkeys(value))


class ComplianceRegulationRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    erase_targets: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    default_residency: str = "eu"


class CompliancePlatformConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    regulations: dict[str, ComplianceRegulationRule] = Field(default_factory=dict)


class AutonomousOptimizationTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_p95_latency_ms: int = Field(ge=1)
    max_error_rate: float = Field(ge=0)
    max_cost_per_1k_tokens_usd: float = Field(ge=0)


class AutonomousOptimizationRoute(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_p95_latency_ms: int = Field(ge=0)
    current_error_rate: float = Field(ge=0)
    current_cost_per_1k_tokens_usd: float = Field(ge=0)
    recommended_priority_delta: int = 0


class AutonomousOptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    targets: dict[str, AutonomousOptimizationTarget] = Field(default_factory=dict)
    routes: dict[str, AutonomousOptimizationRoute] = Field(default_factory=dict)


class AutonomousOptimizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_key: str = Field(min_length=1)
    route_name: str = Field(min_length=1)
    subject_scope: str = Field(min_length=1)


class SovereigntyRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: str
    allowed_regions: list[str] = Field(default_factory=list)


class SovereigntyConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    rules: dict[str, SovereigntyRule] = Field(default_factory=dict)


class SovereigntyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_classification: str = Field(min_length=1)
    source_region: str = Field(min_length=1)
    target_region: str = Field(min_length=1)
    requires_local_processing: bool = False


class IdempotencyCache:
    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[float, dict[str, object]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, object] | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._entries.pop(key, None)
                return None
            return dict(value)

    def set(self, key: str, value: dict[str, object]) -> None:
        expires_at = time.monotonic() + self._ttl_seconds
        with self._lock:
            self._entries[key] = (expires_at, dict(value))


def _planning_config_path_kwargs() -> dict[str, str | None]:
    return {
        b.settings_field: first_non_empty_env(os.environ, *b.env_keys)
        for b in PLANNING_CONFIG_BINDINGS
    }


@lru_cache(maxsize=1)
def get_settings() -> BridgeSettings:
    return BridgeSettings(
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8000")),
        n8n_base_url=os.getenv("N8N_BASE_URL", "http://n8n:5678"),
        op_connect_url=os.getenv("OP_CONNECT_URL", "http://1password-connect-api:8080"),
        op_connect_token=os.getenv("OP_CONNECT_TOKEN"),
        bridge_access_token=os.getenv("BRIDGE_ACCESS_TOKEN"),
        audit_ledger_path=os.getenv(
            "BRIDGE_AUDIT_LEDGER_PATH",
            "/tmp/n8n-bridge/audit-ledger.jsonl",
        ),
        **_planning_config_path_kwargs(),
        request_timeout_seconds=float(os.getenv("BRIDGE_REQUEST_TIMEOUT_SECONDS", "15")),
        idempotency_ttl_seconds=float(os.getenv("BRIDGE_IDEMPOTENCY_TTL_SECONDS", "300")),
    )


def configure_telemetry(service_name: str) -> None:
    tracer_provider = trace.get_tracer_provider()
    if isinstance(tracer_provider, SDKTracerProvider):
        return

    provider = SDKTracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)


def current_trace_id() -> str:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return "0" * 32
    return format(span_context.trace_id, "032x")


def log_event(level: str, event: str, **fields: object) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "event": event,
        "trace_id": current_trace_id(),
        **fields,
    }
    LOGGER.log(getattr(logging, level.upper(), logging.INFO), json.dumps(payload, sort_keys=True))


def canonicalize_payload(payload: Mapping[str, JSONValue]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def build_idempotency_key(webhook_id: str, payload: Mapping[str, JSONValue]) -> str:
    canonical_payload = canonicalize_payload(payload)
    return hashlib.sha256(f"{webhook_id}:{canonical_payload}".encode("utf-8")).hexdigest()


def build_request_id(operation: str, identity: str) -> str:
    return hashlib.sha256(f"{operation}:{identity}".encode("utf-8")).hexdigest()[:32]


class PolicyDeniedError(RuntimeError):
    """Raised when a bridge policy denies tool execution."""


class ToolPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    allowed_webhook_ids: list[str] = Field(default_factory=list)
    allowed_vault_ids: list[str] = Field(default_factory=list)
    allowed_item_ids: list[str] = Field(default_factory=list)
    allowed_field_labels: list[str] = Field(default_factory=list)


class BridgePolicy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    default_action: str = "allow"
    tools: dict[str, ToolPolicy] = Field(default_factory=dict)


class PolicyEngine:
    def __init__(self, policy: BridgePolicy) -> None:
        self._policy = policy

    def authorize(self, tool_name: str, attributes: Mapping[str, str | None]) -> dict[str, JSONValue]:
        tool_policy = self._policy.tools.get(tool_name)
        default_action = self._policy.default_action.lower()
        if tool_policy is None:
            if default_action == "allow":
                return {"allowed": True, "reason": "default allow policy"}
            return {"allowed": False, "reason": f"tool '{tool_name}' is not permitted by policy"}

        if tool_name == "trigger_n8n_workflow":
            webhook_id = attributes.get("webhook_id")
            if self._is_allowed(tool_policy.allowed_webhook_ids, webhook_id):
                return {"allowed": True, "reason": "webhook policy matched"}
            return {
                "allowed": False,
                "reason": f"workflow webhook '{webhook_id}' is not permitted by policy",
            }

        if tool_name == "get_1password_secret":
            vault_id = attributes.get("vault_id")
            item_id = attributes.get("item_id")
            field_label = attributes.get("field_label")

            if not self._is_allowed(tool_policy.allowed_vault_ids, vault_id):
                return {
                    "allowed": False,
                    "reason": f"vault '{vault_id}' is not permitted by policy",
                }
            if not self._is_allowed(tool_policy.allowed_item_ids, item_id):
                return {
                    "allowed": False,
                    "reason": f"item '{item_id}' is not permitted by policy",
                }
            if field_label is not None and not self._is_allowed(tool_policy.allowed_field_labels, field_label):
                return {
                    "allowed": False,
                    "reason": f"field '{field_label}' is not permitted by policy",
                }
            return {"allowed": True, "reason": "secret policy matched"}

        return {"allowed": True, "reason": "tool policy entry matched"}

    @staticmethod
    def _is_allowed(allowed_values: list[str], candidate: str | None) -> bool:
        if not allowed_values:
            return True
        if candidate is None:
            return False
        return "*" in allowed_values or candidate in allowed_values


def _load_policy_file(policy_file_path: str) -> BridgePolicy:
    payload = json.loads(Path(policy_file_path).read_text(encoding="utf-8"))
    return BridgePolicy.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_policy_engine(policy_file_path: str) -> PolicyEngine:
    return PolicyEngine(_load_policy_file(policy_file_path))


def build_policy_engine(settings: BridgeSettings) -> PolicyEngine:
    if settings.mcp_policy_config_path:
        return _cached_policy_engine(settings.mcp_policy_config_path)
    return PolicyEngine(BridgePolicy(default_action="allow"))


class ModelRouter:
    def __init__(self, config: ModelRoutingConfig) -> None:
        self._config = config

    def select_route(self, request: ModelRoutingRequest) -> dict[str, JSONValue]:
        matching_routes = [
            (route_name, route)
            for route_name, route in self._config.routes.items()
            if route_name != self._config.default_route
            if self._route_matches(route, request)
        ]
        if matching_routes:
            selected_name, selected_route = sorted(
                matching_routes,
                key=lambda item: (
                    item[1].priority,
                    0 if item[1].requires_local else 1,
                    item[1].max_latency_ms,
                    item[0],
                ),
            )[0]
            return self._serialize_route(selected_name, selected_route, request)

        if self._config.default_route:
            default_route = self._config.routes.get(self._config.default_route)
            if default_route and self._fallback_matches(default_route, request):
                return self._serialize_route(self._config.default_route, default_route, request, fallback=True)

        raise RuntimeError("No healthy model route matched the request.")

    @staticmethod
    def _projected_cost_usd(route: ModelRouteConfig, request: ModelRoutingRequest) -> float:
        if request.estimated_total_tokens <= 0 or route.estimated_cost_per_1k_tokens_usd <= 0:
            return 0.0
        return (request.estimated_total_tokens / 1000.0) * route.estimated_cost_per_1k_tokens_usd

    @classmethod
    def _governance_matches(cls, route: ModelRouteConfig, request: ModelRoutingRequest) -> bool:
        if route.current_gpu_utilization_percent > route.max_gpu_utilization_percent:
            return False
        if (
            route.max_concurrent_requests is not None
            and route.current_concurrent_requests >= route.max_concurrent_requests
        ):
            return False
        projected_cost_usd = cls._projected_cost_usd(route, request)
        if request.max_cost_usd is not None and projected_cost_usd > request.max_cost_usd:
            return False
        if route.daily_budget_usd is not None and (route.current_spend_usd + projected_cost_usd) > route.daily_budget_usd:
            return False
        return True

    @classmethod
    def _route_matches(cls, route: ModelRouteConfig, request: ModelRoutingRequest) -> bool:
        if not route.healthy:
            return False
        if not cls._governance_matches(route, request):
            return False
        if route.max_latency_ms > request.max_latency_ms:
            return False
        if request.require_local and not route.requires_local:
            return False
        if route.capabilities and "*" not in route.capabilities and request.workload_kind not in route.capabilities:
            return False
        if (
            route.allowed_data_classifications
            and "*" not in route.allowed_data_classifications
            and request.data_classification not in route.allowed_data_classifications
        ):
            return False
        if request.preferred_region:
            if route.regions and "*" not in route.regions and request.preferred_region not in route.regions:
                return False
        return True

    @classmethod
    def _fallback_matches(cls, route: ModelRouteConfig, request: ModelRoutingRequest) -> bool:
        if not route.healthy:
            return False
        if not cls._governance_matches(route, request):
            return False
        if request.require_local and not route.requires_local:
            return False
        if route.capabilities and "*" not in route.capabilities and request.workload_kind not in route.capabilities:
            return False
        if (
            route.allowed_data_classifications
            and "*" not in route.allowed_data_classifications
            and request.data_classification not in route.allowed_data_classifications
        ):
            return False
        return True

    @staticmethod
    def _serialize_route(
        route_name: str,
        route: ModelRouteConfig,
        request: ModelRoutingRequest,
        *,
        fallback: bool = False,
    ) -> dict[str, JSONValue]:
        projected_cost_usd = ModelRouter._projected_cost_usd(route, request)
        return {
            "route_name": route_name,
            "provider": route.provider,
            "base_url": route.base_url,
            "model": route.model,
            "requires_local": route.requires_local,
            "max_latency_ms": route.max_latency_ms,
            "priority": route.priority,
            "current_gpu_utilization_percent": route.current_gpu_utilization_percent,
            "max_gpu_utilization_percent": route.max_gpu_utilization_percent,
            "current_concurrent_requests": route.current_concurrent_requests,
            "max_concurrent_requests": route.max_concurrent_requests,
            "projected_cost_usd": projected_cost_usd,
            "fallback": fallback,
            "replay_fingerprint": build_replay_fingerprint(
                "select_model_route",
                request.model_dump(mode="json"),
            ),
        }


def _load_routing_file(routing_file_path: str) -> ModelRoutingConfig:
    payload = json.loads(Path(routing_file_path).read_text(encoding="utf-8"))
    return ModelRoutingConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_model_router(routing_file_path: str) -> ModelRouter:
    return ModelRouter(_load_routing_file(routing_file_path))


def build_model_router(settings: BridgeSettings) -> ModelRouter:
    if settings.model_routing_config_path:
        return _cached_model_router(settings.model_routing_config_path)
    return ModelRouter(ModelRoutingConfig(default_route=None, routes={}))


class VectorMemoryLifecycleEngine:
    def __init__(self, config: VectorMemoryPolicyConfig) -> None:
        self._config = config

    def plan(self, request: VectorMemoryLifecycleRequest) -> dict[str, JSONValue]:
        evaluation_time = request.evaluation_time or datetime.now(timezone.utc)
        base_rule = self._config.classification_rules.get(
            request.data_classification,
            VectorMemoryRule(retention_days=30, expiry_action=self._config.default_action),
        )
        selected_rule = base_rule
        applied_rule_source = f"classification:{request.data_classification}"

        for pii_label in sorted(request.pii_labels):
            override_rule = self._config.pii_overrides.get(pii_label)
            if override_rule and override_rule.retention_days <= selected_rule.retention_days:
                selected_rule = override_rule
                applied_rule_source = f"pii:{pii_label}"

        retention_expires_at = request.created_at + timedelta(days=selected_rule.retention_days)
        reasons: list[str] = [f"applied {applied_rule_source} retention policy"]

        if request.legal_hold:
            reasons.append("legal hold overrides deletion and expiry actions")
            return self._result(
                action="retain",
                delete_embeddings=False,
                request=request,
                retention_days=selected_rule.retention_days,
                retention_expires_at=retention_expires_at,
                reasons=reasons,
            )

        if request.deletion_requested:
            reasons.append("subject deletion request requires immediate deletion")
            return self._result(
                action="delete",
                delete_embeddings=True,
                request=request,
                retention_days=selected_rule.retention_days,
                retention_expires_at=retention_expires_at,
                reasons=reasons,
            )

        if evaluation_time >= retention_expires_at:
            reasons.append("retention window expired")
            action = selected_rule.expiry_action
            return self._result(
                action=action,
                delete_embeddings=action == "delete",
                request=request,
                retention_days=selected_rule.retention_days,
                retention_expires_at=retention_expires_at,
                reasons=reasons,
            )

        reasons.append("retention window still active")
        return self._result(
            action="retain",
            delete_embeddings=False,
            request=request,
            retention_days=selected_rule.retention_days,
            retention_expires_at=retention_expires_at,
            reasons=reasons,
        )

    @staticmethod
    def _result(
        *,
        action: str,
        delete_embeddings: bool,
        request: VectorMemoryLifecycleRequest,
        retention_days: int,
        retention_expires_at: datetime,
        reasons: list[str],
    ) -> dict[str, JSONValue]:
        return {
            "memory_id": request.memory_id,
            "subject_id": request.subject_id,
            "action": action,
            "delete_embeddings": delete_embeddings,
            "retention_days": retention_days,
            "retention_expires_at": retention_expires_at.isoformat(),
            "reasons": reasons,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_vector_memory_lifecycle",
                request.model_dump(mode="json"),
            ),
        }


def _load_vector_memory_policy_file(policy_file_path: str) -> VectorMemoryPolicyConfig:
    payload = json.loads(Path(policy_file_path).read_text(encoding="utf-8"))
    return VectorMemoryPolicyConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_vector_memory_lifecycle_engine(policy_file_path: str) -> VectorMemoryLifecycleEngine:
    return VectorMemoryLifecycleEngine(_load_vector_memory_policy_file(policy_file_path))


def build_vector_memory_lifecycle_engine(settings: BridgeSettings) -> VectorMemoryLifecycleEngine:
    if settings.vector_memory_config_path:
        return _cached_vector_memory_lifecycle_engine(settings.vector_memory_config_path)
    return VectorMemoryLifecycleEngine(VectorMemoryPolicyConfig())


class ProgressiveRolloutEngine:
    def __init__(self, config: ProgressiveRolloutConfig) -> None:
        self._config = config

    def plan(self, request: ProgressiveRolloutRequest) -> dict[str, JSONValue]:
        entry = self._resolve_entry(request)
        bucket = self._subject_bucket(request.subject_id, request.rollout_key)
        mode = entry.mode.lower()

        if mode == "shadow":
            target = entry.primary_webhook_id or entry.active_prompt_version
            shadow_target = entry.shadow_webhook_id or entry.canary_prompt_version
            return self._serialize_result(
                request=request,
                mode=mode,
                bucket=bucket,
                target=target,
                shadow_target=shadow_target,
            )

        if mode == "canary":
            is_canary = bucket < entry.canary_percentage
            if request.rollout_kind == "workflow":
                target = entry.canary_webhook_id if is_canary else entry.primary_webhook_id
            else:
                target = entry.canary_prompt_version if is_canary else entry.active_prompt_version
            return self._serialize_result(
                request=request,
                mode=mode,
                bucket=bucket,
                target=target,
                shadow_target=None,
            )

        if mode == "full":
            target = entry.primary_webhook_id if request.rollout_kind == "workflow" else entry.active_prompt_version
            return self._serialize_result(
                request=request,
                mode=mode,
                bucket=bucket,
                target=target,
                shadow_target=None,
            )

        raise RuntimeError(f"Unsupported rollout mode '{entry.mode}' for '{request.rollout_key}'.")

    def _resolve_entry(self, request: ProgressiveRolloutRequest) -> ProgressiveRolloutEntry:
        registry = self._config.workflows if request.rollout_kind == "workflow" else self._config.prompts
        entry = registry.get(request.rollout_key)
        if entry is None:
            raise RuntimeError(f"Unknown rollout key '{request.rollout_key}' for kind '{request.rollout_kind}'.")
        return entry

    @staticmethod
    def _subject_bucket(subject_id: str, rollout_key: str) -> int:
        digest = hashlib.sha256(f"{rollout_key}:{subject_id}".encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100

    @staticmethod
    def _serialize_result(
        *,
        request: ProgressiveRolloutRequest,
        mode: str,
        bucket: int,
        target: str | None,
        shadow_target: str | None,
    ) -> dict[str, JSONValue]:
        return {
            "rollout_kind": request.rollout_kind,
            "rollout_key": request.rollout_key,
            "mode": mode,
            "bucket": bucket,
            "target": target,
            "shadow_target": shadow_target,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_progressive_rollout",
                request.model_dump(mode="json"),
            ),
        }


def _load_rollout_file(rollout_file_path: str) -> ProgressiveRolloutConfig:
    payload = json.loads(Path(rollout_file_path).read_text(encoding="utf-8"))
    return ProgressiveRolloutConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_progressive_rollout_engine(rollout_file_path: str) -> ProgressiveRolloutEngine:
    return ProgressiveRolloutEngine(_load_rollout_file(rollout_file_path))


def build_progressive_rollout_engine(settings: BridgeSettings) -> ProgressiveRolloutEngine:
    if settings.progressive_rollout_config_path:
        return _cached_progressive_rollout_engine(settings.progressive_rollout_config_path)
    return ProgressiveRolloutEngine(ProgressiveRolloutConfig())


class FailureModeEngine:
    def __init__(self, config: FailureModeConfig) -> None:
        self._config = config

    def plan(self, request: FailureModeRequest) -> dict[str, JSONValue]:
        rule_key = f"{request.component_name}:{request.failure_type}"
        rule = self._config.rules.get(rule_key, FailureModeRule(action=self._config.default_action))
        retry_allowed = request.retry_count < rule.max_retries
        action = rule.action
        if action == "retry" and not retry_allowed:
            action = "degrade"

        next_backoff_seconds = None
        if action == "retry" and retry_allowed and rule.backoff_seconds:
            next_backoff_seconds = rule.backoff_seconds[min(request.retry_count, len(rule.backoff_seconds) - 1)]

        return {
            "component_name": request.component_name,
            "failure_type": request.failure_type,
            "severity": request.severity,
            "action": action,
            "retry_allowed": retry_allowed,
            "next_backoff_seconds": next_backoff_seconds,
            "fallback_target": rule.fallback_target,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_failure_mode",
                request.model_dump(mode="json"),
            ),
        }


def _load_failure_mode_file(failure_mode_file_path: str) -> FailureModeConfig:
    payload = json.loads(Path(failure_mode_file_path).read_text(encoding="utf-8"))
    return FailureModeConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_failure_mode_engine(failure_mode_file_path: str) -> FailureModeEngine:
    return FailureModeEngine(_load_failure_mode_file(failure_mode_file_path))


def build_failure_mode_engine(settings: BridgeSettings) -> FailureModeEngine:
    if settings.failure_mode_config_path:
        return _cached_failure_mode_engine(settings.failure_mode_config_path)
    return FailureModeEngine(FailureModeConfig())


class ConfidentialExecutionEngine:
    def __init__(self, config: ConfidentialExecutionConfig) -> None:
        self._config = config

    def plan(self, request: ConfidentialExecutionRequest) -> dict[str, JSONValue]:
        matching_targets = [
            (target_name, target)
            for target_name, target in self._config.targets.items()
            if self._target_matches(target, request)
        ]
        if not matching_targets:
            raise RuntimeError("No confidential execution target matched the request.")

        selected_name, selected_target = sorted(
            matching_targets,
            key=lambda item: (
                0 if request.requires_gpu == item[1].supports_gpu else 1,
                0 if (not request.requires_gpu and not item[1].supports_gpu) else 1,
                item[1].priority,
                item[0],
            ),
        )[0]

        return {
            "target_name": selected_name,
            "execution_mode": selected_target.execution_mode,
            "provider": selected_target.provider,
            "endpoint": selected_target.endpoint,
            "attested": selected_target.attested,
            "supports_gpu": selected_target.supports_gpu,
            "provides_workload_identity": selected_target.provides_workload_identity,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_confidential_execution",
                request.model_dump(mode="json"),
            ),
        }

    @staticmethod
    def _target_matches(target: ConfidentialExecutionTarget, request: ConfidentialExecutionRequest) -> bool:
        if not target.healthy:
            return False
        if request.requires_attestation and not target.attested:
            return False
        if request.requires_gpu and not target.supports_gpu:
            return False
        if request.requires_workload_identity and not target.provides_workload_identity:
            return False
        if (
            target.allowed_data_classifications
            and "*" not in target.allowed_data_classifications
            and request.data_classification not in target.allowed_data_classifications
        ):
            return False
        if request.preferred_region:
            if target.regions and "*" not in target.regions and request.preferred_region not in target.regions:
                return False
        return True


def _load_confidential_execution_file(confidential_execution_file_path: str) -> ConfidentialExecutionConfig:
    payload = json.loads(Path(confidential_execution_file_path).read_text(encoding="utf-8"))
    return ConfidentialExecutionConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_confidential_execution_engine(confidential_execution_file_path: str) -> ConfidentialExecutionEngine:
    return ConfidentialExecutionEngine(_load_confidential_execution_file(confidential_execution_file_path))


def build_confidential_execution_engine(settings: BridgeSettings) -> ConfidentialExecutionEngine:
    if settings.confidential_execution_config_path:
        return _cached_confidential_execution_engine(settings.confidential_execution_config_path)
    return ConfidentialExecutionEngine(ConfidentialExecutionConfig())


class AgentControlPlaneEngine:
    def __init__(self, config: AgentControlPlaneConfig) -> None:
        self._config = config

    def plan(self, request: AgentControlPlaneRequest) -> dict[str, JSONValue]:
        tenant = self._config.tenants.get(request.tenant_id)
        if tenant is None:
            raise RuntimeError(f"Unknown tenant '{request.tenant_id}'.")

        disallowed_capabilities = [
            capability for capability in request.requested_capabilities if capability not in tenant.allowed_capabilities
        ]
        if disallowed_capabilities:
            raise RuntimeError(
                f"Capabilities {disallowed_capabilities} are not permitted for tenant '{request.tenant_id}'."
            )

        policy_pack = request.requested_policy_pack or tenant.default_policy_pack
        if policy_pack not in tenant.allowed_policy_packs:
            raise RuntimeError(f"Policy pack '{policy_pack}' is not permitted for tenant '{request.tenant_id}'.")

        quota_class_name = request.requested_quota_class or tenant.default_quota_class
        quota_class = self._config.quota_classes.get(quota_class_name)
        if quota_class is None:
            raise RuntimeError(f"Unknown quota class '{quota_class_name}'.")

        return {
            "tenant_id": request.tenant_id,
            "agent_id": request.agent_id,
            "policy_pack": policy_pack,
            "quota_class": quota_class_name,
            "workspace_id": f"{tenant.workspace_prefix}-{request.agent_id}",
            "max_requests_per_minute": quota_class.max_requests_per_minute,
            "max_parallel_tasks": quota_class.max_parallel_tasks,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_agent_control_plane",
                request.model_dump(mode="json"),
            ),
        }


def _load_agent_control_plane_file(agent_control_plane_file_path: str) -> AgentControlPlaneConfig:
    payload = json.loads(Path(agent_control_plane_file_path).read_text(encoding="utf-8"))
    return AgentControlPlaneConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_agent_control_plane_engine(agent_control_plane_file_path: str) -> AgentControlPlaneEngine:
    return AgentControlPlaneEngine(_load_agent_control_plane_file(agent_control_plane_file_path))


def build_agent_control_plane_engine(settings: BridgeSettings) -> AgentControlPlaneEngine:
    if settings.agent_control_plane_config_path:
        return _cached_agent_control_plane_engine(settings.agent_control_plane_config_path)
    return AgentControlPlaneEngine(AgentControlPlaneConfig())


class CompliancePlatformEngine:
    def __init__(self, config: CompliancePlatformConfig) -> None:
        self._config = config

    def plan(self, request: ComplianceCaseRequest) -> dict[str, JSONValue]:
        rule = self._config.regulations.get(request.regulation)
        if rule is None:
            raise RuntimeError(f"Unknown regulation '{request.regulation}'.")

        if request.case_type == "subject_erasure":
            if request.legal_hold:
                return self._serialize_result(
                    request=request,
                    action="hold",
                    erase_targets=[],
                    evidence_requirements=rule.evidence_requirements,
                    residency_region=rule.default_residency,
                    reasons=["legal hold blocks erasure until released"],
                )
            erase_targets = sorted(target for target in rule.erase_targets if target in request.systems_affected)
            return self._serialize_result(
                request=request,
                action="erase",
                erase_targets=erase_targets,
                evidence_requirements=rule.evidence_requirements,
                residency_region=rule.default_residency,
                reasons=["subject erasure request requires propagation across configured systems"],
            )

        if request.case_type == "audit_evidence":
            return self._serialize_result(
                request=request,
                action="collect_evidence",
                erase_targets=[],
                evidence_requirements=sorted(rule.evidence_requirements),
                residency_region=rule.default_residency,
                reasons=["audit evidence request requires regulation-specific evidence bundle"],
            )

        raise RuntimeError(f"Unsupported compliance case type '{request.case_type}'.")

    @staticmethod
    def _serialize_result(
        *,
        request: ComplianceCaseRequest,
        action: str,
        erase_targets: list[str],
        evidence_requirements: list[str],
        residency_region: str,
        reasons: list[str],
    ) -> dict[str, JSONValue]:
        evidence_bundle_id = hashlib.sha256(
            f"{request.regulation}:{request.case_type}:{request.subject_id}".encode("utf-8")
        ).hexdigest()[:24]
        return {
            "regulation": request.regulation,
            "case_type": request.case_type,
            "subject_id": request.subject_id,
            "action": action,
            "erase_targets": erase_targets,
            "evidence_requirements": sorted(evidence_requirements),
            "evidence_bundle_id": evidence_bundle_id,
            "residency_region": residency_region,
            "reasons": reasons,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_compliance_case",
                request.model_dump(mode="json"),
            ),
        }


def _load_compliance_platform_file(compliance_platform_file_path: str) -> CompliancePlatformConfig:
    payload = json.loads(Path(compliance_platform_file_path).read_text(encoding="utf-8"))
    return CompliancePlatformConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_compliance_platform_engine(compliance_platform_file_path: str) -> CompliancePlatformEngine:
    return CompliancePlatformEngine(_load_compliance_platform_file(compliance_platform_file_path))


def build_compliance_platform_engine(settings: BridgeSettings) -> CompliancePlatformEngine:
    if settings.compliance_platform_config_path:
        return _cached_compliance_platform_engine(settings.compliance_platform_config_path)
    return CompliancePlatformEngine(CompliancePlatformConfig())


class AutonomousOptimizationEngine:
    def __init__(self, config: AutonomousOptimizationConfig) -> None:
        self._config = config

    def plan(self, request: AutonomousOptimizationRequest) -> dict[str, JSONValue]:
        objective = self._config.targets.get(request.objective_key)
        if objective is None:
            raise RuntimeError(f"Unknown optimization objective '{request.objective_key}'.")

        route = self._config.routes.get(request.route_name)
        if route is None:
            raise RuntimeError(f"Unknown optimization route '{request.route_name}'.")

        reasons: list[str] = []
        latency_exceeded = route.current_p95_latency_ms > objective.max_p95_latency_ms
        cost_exceeded = route.current_cost_per_1k_tokens_usd > objective.max_cost_per_1k_tokens_usd
        error_rate_exceeded = route.current_error_rate > objective.max_error_rate

        if latency_exceeded:
            reasons.append("latency target exceeded")
        if cost_exceeded:
            reasons.append("cost target exceeded")
        if error_rate_exceeded:
            reasons.append("error-rate target exceeded")

        if not reasons:
            action = "retain_route"
            budget_adjustment_required = False
            reasons.append("route remains within optimization targets")
        else:
            budget_adjustment_required = cost_exceeded
            if cost_exceeded:
                action = "cap_route_budget"
            elif latency_exceeded:
                action = "deprioritize_route"
            else:
                action = "deprioritize_route"

        return {
            "objective_key": request.objective_key,
            "route_name": request.route_name,
            "action": action,
            "recommended_priority_delta": route.recommended_priority_delta,
            "budget_adjustment_required": budget_adjustment_required,
            "reasons": reasons,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_autonomous_optimization",
                request.model_dump(mode="json"),
            ),
        }


def _load_autonomous_optimization_file(autonomous_optimization_file_path: str) -> AutonomousOptimizationConfig:
    payload = json.loads(Path(autonomous_optimization_file_path).read_text(encoding="utf-8"))
    return AutonomousOptimizationConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_autonomous_optimization_engine(autonomous_optimization_file_path: str) -> AutonomousOptimizationEngine:
    return AutonomousOptimizationEngine(_load_autonomous_optimization_file(autonomous_optimization_file_path))


def build_autonomous_optimization_engine(settings: BridgeSettings) -> AutonomousOptimizationEngine:
    if settings.autonomous_optimization_config_path:
        return _cached_autonomous_optimization_engine(settings.autonomous_optimization_config_path)
    return AutonomousOptimizationEngine(AutonomousOptimizationConfig())


class SovereigntyEngine:
    def __init__(self, config: SovereigntyConfig) -> None:
        self._config = config

    def plan(self, request: SovereigntyRequest) -> dict[str, JSONValue]:
        rule = self._config.rules.get(request.data_classification)
        if rule is None:
            raise RuntimeError(f"Unknown sovereignty rule for classification '{request.data_classification}'.")

        mode = rule.mode
        allowed = True
        reasons: list[str] = []

        if request.requires_local_processing:
            mode = "local_only"
            allowed = request.target_region == "local"
            reasons.append("explicit local processing requirement applied")
        elif mode == "local_only":
            allowed = request.target_region == "local"
            reasons.append("restricted data must remain local")
        elif mode == "in_region":
            allowed = request.target_region in rule.allowed_regions or "*" in rule.allowed_regions
            reasons.append("internal data must remain within allowed residency regions")
        else:
            allowed = True
            reasons.append("cross-boundary transfer is permitted for this classification")

        return {
            "mode": mode,
            "allowed": allowed,
            "allowed_regions": rule.allowed_regions,
            "reasons": reasons,
            "replay_fingerprint": build_replay_fingerprint(
                "plan_sovereignty_mode",
                request.model_dump(mode="json"),
            ),
        }


def _load_sovereignty_file(sovereignty_file_path: str) -> SovereigntyConfig:
    payload = json.loads(Path(sovereignty_file_path).read_text(encoding="utf-8"))
    return SovereigntyConfig.model_validate(payload)


@lru_cache(maxsize=8)
def _cached_sovereignty_engine(sovereignty_file_path: str) -> SovereigntyEngine:
    return SovereigntyEngine(_load_sovereignty_file(sovereignty_file_path))


def build_sovereignty_engine(settings: BridgeSettings) -> SovereigntyEngine:
    if settings.sovereignty_config_path:
        return _cached_sovereignty_engine(settings.sovereignty_config_path)
    return SovereigntyEngine(SovereigntyConfig())


def build_replay_fingerprint(operation: str, request: Mapping[str, JSONValue]) -> str:
    canonical_request = canonicalize_payload(request)
    return hashlib.sha256(f"{operation}:{canonical_request}".encode("utf-8")).hexdigest()


def parse_response_body(response: httpx.Response) -> object:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    return response.text


def verify_bearer_token(authorization_header: str | None, *, expected_token: str) -> bool:
    if not authorization_header:
        return False

    scheme, _, token = authorization_header.partition(" ")
    if scheme != "Bearer" or not token:
        return False

    return hmac.compare_digest(token, expected_token)


def build_observability_headers(request_id: str) -> dict[str, str]:
    return {
        "X-Request-Id": request_id,
        "X-Trace-Id": current_trace_id(),
    }


AUDIT_LEDGER_LOCK = threading.Lock()


def append_audit_record(ledger_path: str, record: Mapping[str, object]) -> None:
    target_path = Path(ledger_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with AUDIT_LEDGER_LOCK:
        with target_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_audit_record(
    settings: BridgeSettings,
    *,
    operation: str,
    request_id: str,
    request: Mapping[str, JSONValue],
    outcome: Mapping[str, JSONValue],
    idempotency_key: str | None = None,
) -> None:
    replay_fingerprint = build_replay_fingerprint(operation, request)
    record = {
        "event_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_name": SERVICE_NAME,
        "operation": operation,
        "request_id": request_id,
        "trace_id": current_trace_id(),
        "replay_fingerprint": replay_fingerprint,
        "idempotency_key": idempotency_key,
        "request": dict(request),
        "outcome": dict(outcome),
    }

    with TRACER.start_as_current_span("mcp.audit_ledger_write") as span:
        span.set_attribute("bridge.audit.operation", operation)
        span.set_attribute("bridge.audit.request_id", request_id)
        span.set_attribute("bridge.audit.replay_fingerprint", replay_fingerprint)
        append_audit_record(settings.audit_ledger_path, record)

    log_event(
        "info",
        "audit_ledger.persisted",
        operation=operation,
        request_id=request_id,
        replay_fingerprint=replay_fingerprint,
        ledger_path=settings.audit_ledger_path,
    )


def enforce_policy(
    settings: BridgeSettings,
    *,
    tool_name: str,
    request_id: str,
    attributes: Mapping[str, str | None],
) -> None:
    policy_engine = build_policy_engine(settings)
    with TRACER.start_as_current_span("mcp.policy_authorize") as span:
        decision = policy_engine.authorize(tool_name, attributes)
        allowed = bool(decision["allowed"])
        reason = str(decision["reason"])
        span.set_attribute("bridge.policy.tool_name", tool_name)
        span.set_attribute("bridge.policy.allowed", allowed)
        span.set_attribute("bridge.policy.reason", reason)

        if allowed:
            log_event(
                "info",
                "policy_engine.allowed",
                tool_name=tool_name,
                request_id=request_id,
                reason=reason,
            )
            return

        write_audit_record(
            settings,
            operation=tool_name,
            request_id=request_id,
            request={k: v for k, v in attributes.items()},
            outcome={
                "policy_decision": "deny",
                "denial_reason": reason,
            },
        )
        log_event(
            "warning",
            "policy_engine.denied",
            tool_name=tool_name,
            request_id=request_id,
            reason=reason,
        )
        raise PolicyDeniedError(reason)


def require_bridge_access_token(settings: BridgeSettings) -> str:
    if not settings.bridge_access_token:
        error_message = "BRIDGE_ACCESS_TOKEN must be configured before starting the MCP bridge."
        log_event("error", "bridge_auth.configuration_error", error=error_message)
        raise RuntimeError(error_message)

    return settings.bridge_access_token


class BridgeAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Starlette, *, expected_token: str, protected_path: str) -> None:
        super().__init__(app)
        self._expected_token = expected_token
        self._protected_path = protected_path.rstrip("/") or "/"

    async def dispatch(self, request: Request, call_next: object) -> JSONResponse | object:
        path = request.url.path
        if path == "/healthz" or not path.startswith(self._protected_path):
            return await call_next(request)

        with TRACER.start_as_current_span("mcp.bridge_auth") as span:
            authorized = verify_bearer_token(
                request.headers.get("Authorization"),
                expected_token=self._expected_token,
            )
            span.set_attribute("bridge.auth.authorized", authorized)
            span.set_attribute("bridge.auth.path", path)
            if authorized:
                return await call_next(request)

            log_event(
                "warning",
                "bridge_auth.denied",
                path=path,
                client_host=request.client.host if request.client else None,
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid bridge bearer token."},
            )


async def healthcheck(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def build_protected_http_app(app: Starlette, settings: BridgeSettings, *, protected_path: str) -> Starlette:
    expected_token = require_bridge_access_token(settings)
    protected_app = Starlette(
        routes=[
            Route("/healthz", endpoint=healthcheck),
            Mount("/", app=app),
        ]
    )
    protected_app.add_middleware(
        BridgeAuthMiddleware,
        expected_token=expected_token,
        protected_path=protected_path,
    )
    return protected_app


def select_field(item: Mapping[str, object], field_label: str) -> Mapping[str, object] | None:
    fields = item.get("fields", [])
    if not isinstance(fields, list):
        return None

    for field in fields:
        if not isinstance(field, Mapping):
            continue
        if field.get("label") == field_label or field.get("id") == field_label:
            return field
    return None


async def trigger_n8n_workflow_impl(
    request: TriggerWorkflowRequest,
    settings: BridgeSettings,
    *,
    client: httpx.AsyncClient,
    cache: IdempotencyCache,
) -> dict[str, object]:
    idempotency_key = build_idempotency_key(request.webhook_id, request.payload)
    request_id = build_request_id("trigger_n8n_workflow", idempotency_key)
    replay_request = {"webhook_id": request.webhook_id, "payload": request.payload}
    webhook_url = f"{settings.n8n_base_url}/webhook/{request.webhook_id}"

    with TRACER.start_as_current_span("mcp.trigger_n8n_workflow") as span:
        span.set_attribute("bridge.webhook_id", request.webhook_id)
        span.set_attribute("bridge.idempotency_key", idempotency_key)
        span.set_attribute("bridge.request_id", request_id)
        log_event(
            "info",
            "trigger_n8n_workflow.start",
            webhook_id=request.webhook_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            webhook_url=webhook_url,
        )
        enforce_policy(
            settings,
            tool_name="trigger_n8n_workflow",
            request_id=request_id,
            attributes={"webhook_id": request.webhook_id},
        )

        cached_result = cache.get(idempotency_key)
        if cached_result is not None:
            span.set_attribute("bridge.deduplicated", True)
            log_event(
                "info",
                "trigger_n8n_workflow.deduplicated",
                webhook_id=request.webhook_id,
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
            return {
                **cached_result,
                "deduplicated": True,
                "idempotency_key": idempotency_key,
                "request_id": request_id,
            }

        try:
            response = await client.post(
                webhook_url,
                json=request.payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": idempotency_key,
                    **build_observability_headers(request_id),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            span.record_exception(exc)
            log_event(
                "error",
                "trigger_n8n_workflow.failed",
                webhook_id=request.webhook_id,
                idempotency_key=idempotency_key,
                request_id=request_id,
                error=str(exc),
            )
            raise RuntimeError(f"n8n webhook request failed for '{request.webhook_id}'") from exc

        result = {
            "status_code": response.status_code,
            "response": parse_response_body(response),
            "request_id": request_id,
        }
        cache.set(idempotency_key, result)
        write_audit_record(
            settings,
            operation="trigger_n8n_workflow",
            request_id=request_id,
            request=replay_request,
            outcome={
                "status_code": response.status_code,
                "deduplicated": False,
                "policy_decision": "allow",
            },
            idempotency_key=idempotency_key,
        )

        log_event(
            "info",
            "trigger_n8n_workflow.completed",
            webhook_id=request.webhook_id,
            idempotency_key=idempotency_key,
            request_id=request_id,
            status_code=response.status_code,
        )
        return {
            **result,
            "deduplicated": False,
            "idempotency_key": idempotency_key,
        }


async def get_1password_secret_impl(
    request: SecretRequest,
    settings: BridgeSettings,
    *,
    client: httpx.AsyncClient,
) -> dict[str, object]:
    request_id = build_request_id(
        "get_1password_secret",
        f"{request.vault_id}:{request.item_id}:{request.field_label or '*'}",
    )
    replay_request = {
        "vault_id": request.vault_id,
        "item_id": request.item_id,
        "field_label": request.field_label,
    }
    with TRACER.start_as_current_span("mcp.get_1password_secret") as span:
        span.set_attribute("bridge.vault_id", request.vault_id)
        span.set_attribute("bridge.item_id", request.item_id)
        span.set_attribute("bridge.request_id", request_id)
        log_event(
            "info",
            "get_1password_secret.start",
            vault_id=request.vault_id,
            item_id=request.item_id,
            field_label=request.field_label,
            request_id=request_id,
        )
        enforce_policy(
            settings,
            tool_name="get_1password_secret",
            request_id=request_id,
            attributes={
                "vault_id": request.vault_id,
                "item_id": request.item_id,
                "field_label": request.field_label,
            },
        )

        if not settings.op_connect_token:
            error_message = "OP_CONNECT_TOKEN is not configured for the bridge."
            log_event(
                "error",
                "get_1password_secret.configuration_error",
                vault_id=request.vault_id,
                item_id=request.item_id,
                request_id=request_id,
                error=error_message,
            )
            raise RuntimeError(error_message)

        try:
            response = await client.get(
                f"{settings.op_connect_url}/v1/vaults/{request.vault_id}/items/{request.item_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {settings.op_connect_token}",
                    **build_observability_headers(request_id),
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            span.record_exception(exc)
            log_event(
                "error",
                "get_1password_secret.failed",
                vault_id=request.vault_id,
                item_id=request.item_id,
                request_id=request_id,
                error=str(exc),
            )
            raise RuntimeError(
                f"1Password Connect request failed for vault '{request.vault_id}' item '{request.item_id}'"
            ) from exc

        item = response.json()
        if request.field_label is None:
            fields = item.get("fields", [])
            available_fields = []
            if isinstance(fields, list):
                available_fields = [
                    str(field.get("label") or field.get("id"))
                    for field in fields
                    if isinstance(field, Mapping)
                ]

            log_event(
                "info",
                "get_1password_secret.inventory",
                vault_id=request.vault_id,
                item_id=request.item_id,
                request_id=request_id,
                available_fields=available_fields,
            )
            write_audit_record(
                settings,
                operation="get_1password_secret",
                request_id=request_id,
                request=replay_request,
                outcome={
                    "available_fields": available_fields,
                    "field_label": request.field_label,
                    "policy_decision": "allow",
                    "secret_value_redacted": True,
                },
            )
            return {
                "vault_id": request.vault_id,
                "item_id": item.get("id", request.item_id),
                "title": item.get("title"),
                "available_fields": available_fields,
                "request_id": request_id,
            }

        matched_field = select_field(item, request.field_label)
        if matched_field is None:
            error_message = (
                f"Field '{request.field_label}' was not found in vault '{request.vault_id}' item '{request.item_id}'."
            )
            log_event(
                "error",
                "get_1password_secret.field_missing",
                vault_id=request.vault_id,
                item_id=request.item_id,
                field_label=request.field_label,
                request_id=request_id,
            )
            raise ValueError(error_message)

        log_event(
            "info",
            "get_1password_secret.completed",
            vault_id=request.vault_id,
            item_id=request.item_id,
            field_label=request.field_label,
            request_id=request_id,
        )
        write_audit_record(
            settings,
            operation="get_1password_secret",
            request_id=request_id,
            request=replay_request,
            outcome={
                "field_label": request.field_label,
                "policy_decision": "allow",
                "secret_value_redacted": True,
                "title": item.get("title"),
            },
        )
        return {
            "vault_id": request.vault_id,
            "item_id": item.get("id", request.item_id),
            "title": item.get("title"),
            "field_label": request.field_label,
            "request_id": request_id,
            "value": matched_field.get("value"),
        }


async def select_model_route_impl(
    request: ModelRoutingRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "select_model_route",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.select_model_route") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.routing.workload_kind", request.workload_kind)
        span.set_attribute("bridge.routing.data_classification", request.data_classification)
        log_event(
            "info",
            "select_model_route.start",
            request_id=request_id,
            workload_kind=request.workload_kind,
            data_classification=request.data_classification,
            require_local=request.require_local,
            preferred_region=request.preferred_region,
        )
        enforce_policy(
            settings,
            tool_name="select_model_route",
            request_id=request_id,
            attributes={
                "workload_kind": request.workload_kind,
                "data_classification": request.data_classification,
            },
        )

        route_result = build_model_router(settings).select_route(request)
        route_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="select_model_route",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "route_name": route_result["route_name"],
                "provider": route_result["provider"],
                "fallback": route_result["fallback"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "select_model_route.completed",
            request_id=request_id,
            route_name=route_result["route_name"],
            provider=route_result["provider"],
            fallback=route_result["fallback"],
        )
        return route_result


async def plan_vector_memory_lifecycle_impl(
    request: VectorMemoryLifecycleRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_vector_memory_lifecycle",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_vector_memory_lifecycle") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.vector_memory.memory_id", request.memory_id)
        span.set_attribute("bridge.vector_memory.subject_id", request.subject_id)
        log_event(
            "info",
            "plan_vector_memory_lifecycle.start",
            request_id=request_id,
            memory_id=request.memory_id,
            subject_id=request.subject_id,
            data_classification=request.data_classification,
            pii_labels=request.pii_labels,
        )
        enforce_policy(
            settings,
            tool_name="plan_vector_memory_lifecycle",
            request_id=request_id,
            attributes={
                "data_classification": request.data_classification,
                "subject_id": request.subject_id,
            },
        )

        lifecycle_result = build_vector_memory_lifecycle_engine(settings).plan(request)
        lifecycle_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_vector_memory_lifecycle",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "action": lifecycle_result["action"],
                "delete_embeddings": lifecycle_result["delete_embeddings"],
                "retention_days": lifecycle_result["retention_days"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_vector_memory_lifecycle.completed",
            request_id=request_id,
            action=lifecycle_result["action"],
            delete_embeddings=lifecycle_result["delete_embeddings"],
            retention_days=lifecycle_result["retention_days"],
        )
        return lifecycle_result


async def plan_progressive_rollout_impl(
    request: ProgressiveRolloutRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_progressive_rollout",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_progressive_rollout") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.rollout.kind", request.rollout_kind)
        span.set_attribute("bridge.rollout.key", request.rollout_key)
        log_event(
            "info",
            "plan_progressive_rollout.start",
            request_id=request_id,
            rollout_kind=request.rollout_kind,
            rollout_key=request.rollout_key,
            subject_id=request.subject_id,
        )
        enforce_policy(
            settings,
            tool_name="plan_progressive_rollout",
            request_id=request_id,
            attributes={
                "rollout_kind": request.rollout_kind,
                "rollout_key": request.rollout_key,
            },
        )

        rollout_result = build_progressive_rollout_engine(settings).plan(request)
        rollout_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_progressive_rollout",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "mode": rollout_result["mode"],
                "target": rollout_result["target"],
                "shadow_target": rollout_result["shadow_target"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_progressive_rollout.completed",
            request_id=request_id,
            rollout_kind=request.rollout_kind,
            rollout_key=request.rollout_key,
            mode=rollout_result["mode"],
            target=rollout_result["target"],
            shadow_target=rollout_result["shadow_target"],
        )
        return rollout_result


async def plan_failure_mode_impl(
    request: FailureModeRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_failure_mode",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_failure_mode") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.failure.component_name", request.component_name)
        span.set_attribute("bridge.failure.failure_type", request.failure_type)
        log_event(
            "info",
            "plan_failure_mode.start",
            request_id=request_id,
            component_name=request.component_name,
            failure_type=request.failure_type,
            severity=request.severity,
            retry_count=request.retry_count,
        )
        enforce_policy(
            settings,
            tool_name="plan_failure_mode",
            request_id=request_id,
            attributes={
                "component_name": request.component_name,
                "failure_type": request.failure_type,
            },
        )

        failure_result = build_failure_mode_engine(settings).plan(request)
        failure_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_failure_mode",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "action": failure_result["action"],
                "retry_allowed": failure_result["retry_allowed"],
                "fallback_target": failure_result["fallback_target"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_failure_mode.completed",
            request_id=request_id,
            component_name=request.component_name,
            failure_type=request.failure_type,
            action=failure_result["action"],
            retry_allowed=failure_result["retry_allowed"],
            fallback_target=failure_result["fallback_target"],
        )
        return failure_result


async def plan_confidential_execution_impl(
    request: ConfidentialExecutionRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_confidential_execution",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_confidential_execution") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.confidential.workload_kind", request.workload_kind)
        span.set_attribute("bridge.confidential.data_classification", request.data_classification)
        log_event(
            "info",
            "plan_confidential_execution.start",
            request_id=request_id,
            workload_kind=request.workload_kind,
            data_classification=request.data_classification,
            requires_attestation=request.requires_attestation,
            requires_gpu=request.requires_gpu,
            requires_workload_identity=request.requires_workload_identity,
        )
        enforce_policy(
            settings,
            tool_name="plan_confidential_execution",
            request_id=request_id,
            attributes={
                "workload_kind": request.workload_kind,
                "data_classification": request.data_classification,
            },
        )

        confidential_result = build_confidential_execution_engine(settings).plan(request)
        confidential_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_confidential_execution",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "target_name": confidential_result["target_name"],
                "execution_mode": confidential_result["execution_mode"],
                "provider": confidential_result["provider"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_confidential_execution.completed",
            request_id=request_id,
            target_name=confidential_result["target_name"],
            execution_mode=confidential_result["execution_mode"],
            provider=confidential_result["provider"],
        )
        return confidential_result


async def plan_agent_control_plane_impl(
    request: AgentControlPlaneRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_agent_control_plane",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_agent_control_plane") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.agent_control.tenant_id", request.tenant_id)
        span.set_attribute("bridge.agent_control.agent_id", request.agent_id)
        log_event(
            "info",
            "plan_agent_control_plane.start",
            request_id=request_id,
            tenant_id=request.tenant_id,
            agent_id=request.agent_id,
            requested_capabilities=request.requested_capabilities,
        )
        enforce_policy(
            settings,
            tool_name="plan_agent_control_plane",
            request_id=request_id,
            attributes={
                "tenant_id": request.tenant_id,
                "agent_id": request.agent_id,
            },
        )

        control_result = build_agent_control_plane_engine(settings).plan(request)
        control_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_agent_control_plane",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "policy_pack": control_result["policy_pack"],
                "quota_class": control_result["quota_class"],
                "workspace_id": control_result["workspace_id"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_agent_control_plane.completed",
            request_id=request_id,
            tenant_id=request.tenant_id,
            agent_id=request.agent_id,
            policy_pack=control_result["policy_pack"],
            quota_class=control_result["quota_class"],
            workspace_id=control_result["workspace_id"],
        )
        return control_result


async def plan_compliance_case_impl(
    request: ComplianceCaseRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_compliance_case",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_compliance_case") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.compliance.regulation", request.regulation)
        span.set_attribute("bridge.compliance.case_type", request.case_type)
        log_event(
            "info",
            "plan_compliance_case.start",
            request_id=request_id,
            regulation=request.regulation,
            case_type=request.case_type,
            subject_id=request.subject_id,
            systems_affected=request.systems_affected,
        )
        enforce_policy(
            settings,
            tool_name="plan_compliance_case",
            request_id=request_id,
            attributes={
                "regulation": request.regulation,
                "case_type": request.case_type,
            },
        )

        compliance_result = build_compliance_platform_engine(settings).plan(request)
        compliance_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_compliance_case",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "action": compliance_result["action"],
                "evidence_bundle_id": compliance_result["evidence_bundle_id"],
                "residency_region": compliance_result["residency_region"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_compliance_case.completed",
            request_id=request_id,
            regulation=request.regulation,
            case_type=request.case_type,
            action=compliance_result["action"],
            evidence_bundle_id=compliance_result["evidence_bundle_id"],
        )
        return compliance_result


async def plan_autonomous_optimization_impl(
    request: AutonomousOptimizationRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_autonomous_optimization",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_autonomous_optimization") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.optimization.objective_key", request.objective_key)
        span.set_attribute("bridge.optimization.route_name", request.route_name)
        log_event(
            "info",
            "plan_autonomous_optimization.start",
            request_id=request_id,
            objective_key=request.objective_key,
            route_name=request.route_name,
            subject_scope=request.subject_scope,
        )
        enforce_policy(
            settings,
            tool_name="plan_autonomous_optimization",
            request_id=request_id,
            attributes={
                "objective_key": request.objective_key,
                "route_name": request.route_name,
            },
        )

        optimization_result = build_autonomous_optimization_engine(settings).plan(request)
        optimization_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_autonomous_optimization",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "action": optimization_result["action"],
                "recommended_priority_delta": optimization_result["recommended_priority_delta"],
                "budget_adjustment_required": optimization_result["budget_adjustment_required"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_autonomous_optimization.completed",
            request_id=request_id,
            objective_key=request.objective_key,
            route_name=request.route_name,
            action=optimization_result["action"],
            budget_adjustment_required=optimization_result["budget_adjustment_required"],
        )
        return optimization_result


async def plan_sovereignty_mode_impl(
    request: SovereigntyRequest,
    settings: BridgeSettings,
) -> dict[str, JSONValue]:
    request_id = build_request_id(
        "plan_sovereignty_mode",
        canonicalize_payload(request.model_dump(mode="json")),
    )

    with TRACER.start_as_current_span("mcp.plan_sovereignty_mode") as span:
        span.set_attribute("bridge.request_id", request_id)
        span.set_attribute("bridge.sovereignty.data_classification", request.data_classification)
        log_event(
            "info",
            "plan_sovereignty_mode.start",
            request_id=request_id,
            data_classification=request.data_classification,
            source_region=request.source_region,
            target_region=request.target_region,
            requires_local_processing=request.requires_local_processing,
        )
        enforce_policy(
            settings,
            tool_name="plan_sovereignty_mode",
            request_id=request_id,
            attributes={
                "data_classification": request.data_classification,
                "target_region": request.target_region,
            },
        )

        sovereignty_result = build_sovereignty_engine(settings).plan(request)
        sovereignty_result["request_id"] = request_id
        write_audit_record(
            settings,
            operation="plan_sovereignty_mode",
            request_id=request_id,
            request=request.model_dump(mode="json"),
            outcome={
                "mode": sovereignty_result["mode"],
                "allowed": sovereignty_result["allowed"],
                "policy_decision": "allow",
            },
        )
        log_event(
            "info",
            "plan_sovereignty_mode.completed",
            request_id=request_id,
            mode=sovereignty_result["mode"],
            allowed=sovereignty_result["allowed"],
        )
        return sovereignty_result


DEFAULT_CACHE = IdempotencyCache(ttl_seconds=get_settings().idempotency_ttl_seconds)


@MCP_SERVER.tool()
async def trigger_n8n_workflow(webhook_id: str, payload: dict[str, JSONValue]) -> dict[str, object]:
    """Trigger an n8n workflow webhook with deterministic idempotency protection."""
    settings = get_settings()
    request = TriggerWorkflowRequest(webhook_id=webhook_id, payload=payload)
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        return await trigger_n8n_workflow_impl(request, settings, client=client, cache=DEFAULT_CACHE)


@MCP_SERVER.tool()
async def get_1password_secret(
    vault_id: str,
    item_id: str,
    field_label: str | None = None,
) -> dict[str, object]:
    """Read a single secret field or inspect available fields from a local 1Password Connect item."""
    settings = get_settings()
    request = SecretRequest(vault_id=vault_id, item_id=item_id, field_label=field_label)
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        return await get_1password_secret_impl(request, settings, client=client)


@MCP_SERVER.tool()
async def select_model_route(
    workload_kind: str,
    data_classification: str,
    max_latency_ms: int,
    require_local: bool = False,
    preferred_region: str | None = None,
) -> dict[str, JSONValue]:
    """Select the most appropriate model route based on sensitivity, locality, and latency budget."""
    settings = get_settings()
    request = ModelRoutingRequest(
        workload_kind=workload_kind,
        data_classification=data_classification,
        max_latency_ms=max_latency_ms,
        require_local=require_local,
        preferred_region=preferred_region,
    )
    return await select_model_route_impl(request, settings)


@MCP_SERVER.tool()
async def plan_vector_memory_lifecycle(
    memory_id: str,
    subject_id: str,
    data_classification: str,
    pii_labels: list[str],
    created_at: str,
    last_accessed_at: str | None = None,
    evaluation_time: str | None = None,
    legal_hold: bool = False,
    deletion_requested: bool = False,
) -> dict[str, JSONValue]:
    """Plan retention, deletion, and redaction actions for vector memory records containing PII."""
    settings = get_settings()
    request = VectorMemoryLifecycleRequest(
        memory_id=memory_id,
        subject_id=subject_id,
        data_classification=data_classification,
        pii_labels=pii_labels,
        created_at=created_at,
        last_accessed_at=last_accessed_at,
        evaluation_time=evaluation_time,
        legal_hold=legal_hold,
        deletion_requested=deletion_requested,
    )
    return await plan_vector_memory_lifecycle_impl(request, settings)


@MCP_SERVER.tool()
async def plan_progressive_rollout(
    rollout_kind: str,
    rollout_key: str,
    subject_id: str,
) -> dict[str, JSONValue]:
    """Plan a deterministic rollout decision for workflows or prompt versions."""
    settings = get_settings()
    request = ProgressiveRolloutRequest(
        rollout_kind=rollout_kind,
        rollout_key=rollout_key,
        subject_id=subject_id,
    )
    return await plan_progressive_rollout_impl(request, settings)


@MCP_SERVER.tool()
async def plan_failure_mode(
    component_name: str,
    failure_type: str,
    severity: str,
    retry_count: int,
    data_classification: str,
) -> dict[str, JSONValue]:
    """Plan deterministic retry, failover, degrade, or halt actions for known failure modes."""
    settings = get_settings()
    request = FailureModeRequest(
        component_name=component_name,
        failure_type=failure_type,
        severity=severity,
        retry_count=retry_count,
        data_classification=data_classification,
    )
    return await plan_failure_mode_impl(request, settings)


@MCP_SERVER.tool()
async def plan_confidential_execution(
    workload_kind: str,
    data_classification: str,
    requires_attestation: bool,
    requires_gpu: bool,
    requires_workload_identity: bool,
    preferred_region: str | None = None,
) -> dict[str, JSONValue]:
    """Plan the safest attested or isolated execution target for sensitive workloads."""
    settings = get_settings()
    request = ConfidentialExecutionRequest(
        workload_kind=workload_kind,
        data_classification=data_classification,
        requires_attestation=requires_attestation,
        requires_gpu=requires_gpu,
        requires_workload_identity=requires_workload_identity,
        preferred_region=preferred_region,
    )
    return await plan_confidential_execution_impl(request, settings)


@MCP_SERVER.tool()
async def plan_agent_control_plane(
    tenant_id: str,
    agent_id: str,
    requested_capabilities: list[str],
    requested_policy_pack: str | None = None,
    requested_quota_class: str | None = None,
) -> dict[str, JSONValue]:
    """Plan tenant, quota, workspace, and policy-pack assignment for an agent."""
    settings = get_settings()
    request = AgentControlPlaneRequest(
        tenant_id=tenant_id,
        agent_id=agent_id,
        requested_capabilities=requested_capabilities,
        requested_policy_pack=requested_policy_pack,
        requested_quota_class=requested_quota_class,
    )
    return await plan_agent_control_plane_impl(request, settings)


@MCP_SERVER.tool()
async def plan_compliance_case(
    regulation: str,
    case_type: str,
    subject_id: str,
    systems_affected: list[str],
    data_classification: str,
    legal_hold: bool = False,
) -> dict[str, JSONValue]:
    """Plan regulation-specific erase, evidence, and residency actions for an AI compliance case."""
    settings = get_settings()
    request = ComplianceCaseRequest(
        regulation=regulation,
        case_type=case_type,
        subject_id=subject_id,
        systems_affected=systems_affected,
        data_classification=data_classification,
        legal_hold=legal_hold,
    )
    return await plan_compliance_case_impl(request, settings)


@MCP_SERVER.tool()
async def plan_autonomous_optimization(
    objective_key: str,
    route_name: str,
    subject_scope: str,
) -> dict[str, JSONValue]:
    """Plan deterministic optimization actions for a route under a named objective."""
    settings = get_settings()
    request = AutonomousOptimizationRequest(
        objective_key=objective_key,
        route_name=route_name,
        subject_scope=subject_scope,
    )
    return await plan_autonomous_optimization_impl(request, settings)


@MCP_SERVER.tool()
async def plan_sovereignty_mode(
    data_classification: str,
    source_region: str,
    target_region: str,
    requires_local_processing: bool = False,
) -> dict[str, JSONValue]:
    """Plan whether a workload must remain local, remain in-region, or may cross boundaries."""
    settings = get_settings()
    request = SovereigntyRequest(
        data_classification=data_classification,
        source_region=source_region,
        target_region=target_region,
        requires_local_processing=requires_local_processing,
    )
    return await plan_sovereignty_mode_impl(request, settings)


def main() -> None:
    settings = get_settings()
    configure_telemetry(os.getenv("OTEL_SERVICE_NAME", SERVICE_NAME))
    MCP_SERVER.settings.host = settings.host
    MCP_SERVER.settings.port = settings.port
    protected_app = build_protected_http_app(
        MCP_SERVER.streamable_http_app(),
        settings,
        protected_path=MCP_SERVER.settings.streamable_http_path,
    )
    log_event(
        "info",
        "mcp_server.starting",
        host=settings.host,
        port=settings.port,
        protected_path=MCP_SERVER.settings.streamable_http_path,
    )
    uvicorn.run(
        protected_app,
        host=settings.host,
        port=settings.port,
        log_level=MCP_SERVER.settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
