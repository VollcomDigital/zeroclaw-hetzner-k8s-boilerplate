from __future__ import annotations

import asyncio

import httpx
import pytest
import respx
from starlette.applications import Starlette
from starlette.responses import JSONResponse

import n8n_bridge.server as server
from n8n_bridge.server import (
    BridgeSettings,
    IdempotencyCache,
    SecretRequest,
    TriggerWorkflowRequest,
    build_protected_http_app,
    build_idempotency_key,
    require_bridge_access_token,
    get_1password_secret_impl,
    trigger_n8n_workflow_impl,
    verify_bearer_token,
)


def test_tracer_is_lazy_wrapper() -> None:
    from n8n_bridge.server import _LazyTracer

    assert isinstance(server.TRACER, _LazyTracer)
    assert callable(server.TRACER.start_as_current_span)


@pytest.mark.asyncio
async def test_idempotency_cache_purges_expired_on_set_without_get(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = IdempotencyCache(ttl_seconds=100.0)
    clock = [0.0]
    monkeypatch.setattr(server.time, "monotonic", lambda: clock[0])
    await cache.set("stale", {"v": 1})
    assert len(cache._entries) == 1
    clock[0] = 200.0
    await cache.set("fresh", {"v": 2})
    assert list(cache._entries) == ["fresh"]


@pytest.mark.asyncio
async def test_idempotency_cache_purges_expired_on_get_for_unrelated_key(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = IdempotencyCache(ttl_seconds=100.0)
    clock = [0.0]
    monkeypatch.setattr(server.time, "monotonic", lambda: clock[0])
    await cache.set("stale", {"v": 1})
    clock[0] = 200.0
    assert await cache.get("other") is None
    assert cache._entries == {}


@pytest.mark.asyncio
async def test_idempotency_cache_concurrent_reads_do_not_block_event_loop() -> None:
    cache = IdempotencyCache(ttl_seconds=300.0)
    await cache.set("k", {"status_code": 200, "response": {}, "request_id": "r1"})
    results = await asyncio.gather(*(cache.get("k") for _ in range(32)))
    assert all(r is not None and r["request_id"] == "r1" for r in results)


def test_idempotency_cache_uses_asyncio_lock_not_threading() -> None:
    cache = IdempotencyCache(ttl_seconds=60.0)
    assert isinstance(cache._lock, asyncio.Lock)


def test_build_idempotency_key_is_order_insensitive() -> None:
    first = build_idempotency_key("workflow-demo", {"alpha": 1, "beta": 2})
    second = build_idempotency_key("workflow-demo", {"beta": 2, "alpha": 1})
    assert first == second


def test_verify_bearer_token_rejects_missing_and_malformed_headers() -> None:
    assert verify_bearer_token(None, expected_token="bridge-token") is False
    assert verify_bearer_token("", expected_token="bridge-token") is False
    assert verify_bearer_token("Basic bridge-token", expected_token="bridge-token") is False
    assert verify_bearer_token("Bearer wrong-token", expected_token="bridge-token") is False
    assert verify_bearer_token("Bearer bridge-token", expected_token="bridge-token") is True


def test_require_bridge_access_token_raises_for_missing_configuration() -> None:
    settings = BridgeSettings(bridge_access_token=None)

    with pytest.raises(RuntimeError, match="BRIDGE_ACCESS_TOKEN must be configured"):
        require_bridge_access_token(settings)


@pytest.mark.asyncio
async def test_build_protected_http_app_blocks_unauthorized_mcp_requests() -> None:
    app = build_protected_http_app(
        Starlette(),
        BridgeSettings(bridge_access_token="bridge-token"),
        protected_path="/mcp",
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        unauthorized = await client.get("/mcp")
        health = await client.get("/healthz")
        authorized = await client.get("/mcp", headers={"Authorization": "Bearer bridge-token"})

    assert unauthorized.status_code == 401
    assert unauthorized.json()["detail"] == "Missing or invalid bridge bearer token."
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert authorized.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_trigger_n8n_workflow_deduplicates_identical_payloads() -> None:
    route = respx.post("http://n8n:5678/webhook/run-demo").mock(
        return_value=httpx.Response(200, json={"accepted": True})
    )
    settings = BridgeSettings(n8n_base_url="http://n8n:5678")
    request = TriggerWorkflowRequest(webhook_id="run-demo", payload={"job": "sync", "run": 1})
    cache = IdempotencyCache(ttl_seconds=300)

    async with httpx.AsyncClient() as client:
        first = await trigger_n8n_workflow_impl(request, settings, client=client, cache=cache)
        second = await trigger_n8n_workflow_impl(request, settings, client=client, cache=cache)

    assert route.call_count == 1
    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert second["idempotency_key"] == first["idempotency_key"]
    assert first["request_id"] == second["request_id"]

    sent_headers = route.calls[0].request.headers
    assert sent_headers["X-Idempotency-Key"] == first["idempotency_key"]
    assert sent_headers["X-Request-Id"] == first["request_id"]
    assert sent_headers["X-Trace-Id"]


@pytest.mark.asyncio
@respx.mock
async def test_trigger_n8n_workflow_raises_on_http_failure() -> None:
    respx.post("http://n8n:5678/webhook/broken").mock(return_value=httpx.Response(502))
    settings = BridgeSettings(n8n_base_url="http://n8n:5678")
    request = TriggerWorkflowRequest(webhook_id="broken", payload={"job": "sync"})
    cache = IdempotencyCache(ttl_seconds=300)

    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="n8n webhook request failed"):
            await trigger_n8n_workflow_impl(request, settings, client=client, cache=cache)


@pytest.mark.asyncio
@respx.mock
async def test_get_1password_secret_returns_selected_field_value() -> None:
    respx.get("http://1password-connect-api:8080/v1/vaults/vault-dev/items/item-001").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "item-001",
                "title": "Demo Secret",
                "fields": [
                    {"id": "username", "label": "username", "value": "agent"},
                    {"id": "api-key", "label": "api-key", "value": "super-secret"},
                ],
            },
        )
    )
    settings = BridgeSettings(
        op_connect_url="http://1password-connect-api:8080",
        op_connect_token="development-token",
    )
    request = SecretRequest(vault_id="vault-dev", item_id="item-001", field_label="api-key")

    async with httpx.AsyncClient() as client:
        result = await get_1password_secret_impl(request, settings, client=client)

    assert result["field_label"] == "api-key"
    assert result["value"] == "super-secret"
    assert result["request_id"]


@pytest.mark.asyncio
@respx.mock
async def test_get_1password_secret_raises_value_error_when_field_label_missing() -> None:
    respx.get("http://1password-connect-api:8080/v1/vaults/vault-dev/items/item-001").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "item-001",
                "title": "Demo Secret",
                "fields": [
                    {"id": "username", "label": "username", "value": "agent"},
                ],
            },
        )
    )
    settings = BridgeSettings(
        op_connect_url="http://1password-connect-api:8080",
        op_connect_token="development-token",
    )
    request = SecretRequest(vault_id="vault-dev", item_id="item-001", field_label="api-key")

    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError) as exc_info:
            await get_1password_secret_impl(request, settings, client=client)

    assert str(exc_info.value) == (
        "Field 'api-key' was not found in vault 'vault-dev' item 'item-001'."
    )


@pytest.mark.asyncio
@respx.mock
async def test_get_1password_secret_raises_value_error_when_field_id_not_in_item() -> None:
    """select_field matches id or label; missing both should raise the same ValueError shape."""
    respx.get("http://1password-connect-api:8080/v1/vaults/vault-dev/items/item-001").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "item-001",
                "title": "Demo Secret",
                "fields": [{"id": "only-id", "label": "visible-label", "value": "x"}],
            },
        )
    )
    settings = BridgeSettings(
        op_connect_url="http://1password-connect-api:8080",
        op_connect_token="development-token",
    )
    request = SecretRequest(vault_id="vault-dev", item_id="item-001", field_label="wrong-id")

    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError) as exc_info:
            await get_1password_secret_impl(request, settings, client=client)

    assert str(exc_info.value) == (
        "Field 'wrong-id' was not found in vault 'vault-dev' item 'item-001'."
    )


@pytest.mark.asyncio
@respx.mock
async def test_get_1password_secret_returns_inventory_when_field_not_requested() -> None:
    route = respx.get("http://1password-connect-api:8080/v1/vaults/vault-dev/items/item-001").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "item-001",
                "title": "Demo Secret",
                "fields": [
                    {"id": "username", "label": "username", "value": "agent"},
                    {"id": "api-key", "label": "api-key", "value": "super-secret"},
                ],
            },
        )
    )
    settings = BridgeSettings(
        op_connect_url="http://1password-connect-api:8080",
        op_connect_token="development-token",
    )
    request = SecretRequest(vault_id="vault-dev", item_id="item-001")

    async with httpx.AsyncClient() as client:
        result = await get_1password_secret_impl(request, settings, client=client)

    assert result["title"] == "Demo Secret"
    assert result["available_fields"] == ["username", "api-key"]
    assert result["request_id"]
    assert route.calls[0].request.headers["X-Request-Id"] == result["request_id"]
    assert route.calls[0].request.headers["X-Trace-Id"]


@pytest.mark.asyncio
async def test_get_1password_secret_requires_connect_token() -> None:
    settings = BridgeSettings(op_connect_token=None)
    request = SecretRequest(vault_id="vault-dev", item_id="item-001", field_label="api-key")

    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="OP_CONNECT_TOKEN is not configured"):
            await get_1password_secret_impl(request, settings, client=client)
