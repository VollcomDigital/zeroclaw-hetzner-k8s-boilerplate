from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_settings() -> BridgeSettings:
    return BridgeSettings(
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8000")),
        n8n_base_url=os.getenv("N8N_BASE_URL", "http://n8n:5678"),
        op_connect_url=os.getenv("OP_CONNECT_URL", "http://1password-connect-api:8080"),
        op_connect_token=os.getenv("OP_CONNECT_TOKEN"),
        bridge_access_token=os.getenv("BRIDGE_ACCESS_TOKEN"),
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
    webhook_url = f"{settings.n8n_base_url}/webhook/{request.webhook_id}"

    with TRACER.start_as_current_span("mcp.trigger_n8n_workflow") as span:
        span.set_attribute("bridge.webhook_id", request.webhook_id)
        span.set_attribute("bridge.idempotency_key", idempotency_key)
        log_event(
            "info",
            "trigger_n8n_workflow.start",
            webhook_id=request.webhook_id,
            idempotency_key=idempotency_key,
            webhook_url=webhook_url,
        )

        cached_result = cache.get(idempotency_key)
        if cached_result is not None:
            span.set_attribute("bridge.deduplicated", True)
            log_event(
                "info",
                "trigger_n8n_workflow.deduplicated",
                webhook_id=request.webhook_id,
                idempotency_key=idempotency_key,
            )
            return {**cached_result, "deduplicated": True, "idempotency_key": idempotency_key}

        try:
            response = await client.post(
                webhook_url,
                json=request.payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": idempotency_key,
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
                error=str(exc),
            )
            raise RuntimeError(f"n8n webhook request failed for '{request.webhook_id}'") from exc

        result = {
            "status_code": response.status_code,
            "response": parse_response_body(response),
        }
        cache.set(idempotency_key, result)

        log_event(
            "info",
            "trigger_n8n_workflow.completed",
            webhook_id=request.webhook_id,
            idempotency_key=idempotency_key,
            status_code=response.status_code,
        )
        return {**result, "deduplicated": False, "idempotency_key": idempotency_key}


async def get_1password_secret_impl(
    request: SecretRequest,
    settings: BridgeSettings,
    *,
    client: httpx.AsyncClient,
) -> dict[str, object]:
    with TRACER.start_as_current_span("mcp.get_1password_secret") as span:
        span.set_attribute("bridge.vault_id", request.vault_id)
        span.set_attribute("bridge.item_id", request.item_id)
        log_event(
            "info",
            "get_1password_secret.start",
            vault_id=request.vault_id,
            item_id=request.item_id,
            field_label=request.field_label,
        )

        if not settings.op_connect_token:
            error_message = "OP_CONNECT_TOKEN is not configured for the bridge."
            log_event(
                "error",
                "get_1password_secret.configuration_error",
                vault_id=request.vault_id,
                item_id=request.item_id,
                error=error_message,
            )
            raise RuntimeError(error_message)

        try:
            response = await client.get(
                f"{settings.op_connect_url}/v1/vaults/{request.vault_id}/items/{request.item_id}",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {settings.op_connect_token}",
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
                available_fields=available_fields,
            )
            return {
                "vault_id": request.vault_id,
                "item_id": item.get("id", request.item_id),
                "title": item.get("title"),
                "available_fields": available_fields,
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
            )
            raise ValueError(error_message)

        log_event(
            "info",
            "get_1password_secret.completed",
            vault_id=request.vault_id,
            item_id=request.item_id,
            field_label=request.field_label,
        )
        return {
            "vault_id": request.vault_id,
            "item_id": item.get("id", request.item_id),
            "title": item.get("title"),
            "field_label": request.field_label,
            "value": matched_field.get("value"),
        }


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
