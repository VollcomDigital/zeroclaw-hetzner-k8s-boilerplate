from __future__ import annotations

import os

import httpx
import pytest
import respx

from n8n_bridge.server import get_1password_secret, get_settings, trigger_n8n_workflow


@pytest.fixture(autouse=True)
def configure_bridge_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("N8N_BASE_URL", "http://n8n:5678")
    monkeypatch.setenv("OP_CONNECT_URL", "http://1password-connect-api:8080")
    monkeypatch.setenv("OP_CONNECT_TOKEN", "integration-connect-token")
    monkeypatch.setenv("BRIDGE_ACCESS_TOKEN", "integration-bridge-token")
    get_settings.cache_clear()


def require_matrix_scenario(name: str) -> None:
    configured_scenario = os.getenv("INTEGRATION_SCENARIO")
    if configured_scenario and configured_scenario != name:
        pytest.skip(f"Scenario '{name}' is not selected for this matrix run.")


@pytest.mark.asyncio
@respx.mock
async def test_toolchain_integration_matrix() -> None:
    require_matrix_scenario("toolchain")

    workflow_route = respx.post("http://n8n:5678/webhook/integration-toolchain").mock(
        return_value=httpx.Response(200, json={"executionId": "exec-123", "accepted": True})
    )
    secret_route = respx.get("http://1password-connect-api:8080/v1/vaults/vault-demo/items/item-001").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "item-001",
                "title": "Service Credentials",
                "fields": [
                    {"id": "username", "label": "username", "value": "agent"},
                    {"id": "api-key", "label": "api-key", "value": "super-secret"},
                ],
            },
        )
    )

    workflow_result = await trigger_n8n_workflow(
        "integration-toolchain",
        {"action": "sync", "tenant": "demo"},
    )
    secret_result = await get_1password_secret("vault-demo", "item-001", "api-key")

    assert workflow_route.call_count == 1
    assert secret_route.call_count == 1
    assert workflow_result["deduplicated"] is False
    assert workflow_result["response"]["executionId"] == "exec-123"
    assert secret_result["field_label"] == "api-key"
    assert secret_result["value"] == "super-secret"


@pytest.mark.asyncio
@respx.mock
async def test_idempotency_integration_matrix() -> None:
    require_matrix_scenario("idempotency")

    workflow_route = respx.post("http://n8n:5678/webhook/integration-idempotency").mock(
        return_value=httpx.Response(200, json={"executionId": "exec-789", "accepted": True})
    )

    first_result = await trigger_n8n_workflow(
        "integration-idempotency",
        {"action": "sync", "tenant": "demo", "attempt": 1},
    )
    second_result = await trigger_n8n_workflow(
        "integration-idempotency",
        {"tenant": "demo", "attempt": 1, "action": "sync"},
    )

    assert workflow_route.call_count == 1
    assert first_result["deduplicated"] is False
    assert second_result["deduplicated"] is True
    assert second_result["idempotency_key"] == first_result["idempotency_key"]
