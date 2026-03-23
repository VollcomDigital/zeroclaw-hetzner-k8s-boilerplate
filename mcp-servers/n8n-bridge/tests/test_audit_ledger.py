from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from n8n_bridge.server import (
    BridgeSettings,
    IdempotencyCache,
    SecretRequest,
    TriggerWorkflowRequest,
    build_replay_fingerprint,
    get_1password_secret_impl,
    trigger_n8n_workflow_impl,
)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_build_replay_fingerprint_is_order_insensitive() -> None:
    first = build_replay_fingerprint(
        "trigger_n8n_workflow",
        {"payload": {"alpha": 1, "beta": 2}, "webhook_id": "run-demo"},
    )
    second = build_replay_fingerprint(
        "trigger_n8n_workflow",
        {"webhook_id": "run-demo", "payload": {"beta": 2, "alpha": 1}},
    )

    assert first == second


@pytest.mark.asyncio
@respx.mock
async def test_trigger_n8n_workflow_persists_audit_ledger_record(tmp_path: Path) -> None:
    respx.post("http://n8n:5678/webhook/run-demo").mock(
        return_value=httpx.Response(200, json={"accepted": True})
    )
    ledger_path = tmp_path / "audit-ledger.jsonl"
    settings = BridgeSettings(
        n8n_base_url="http://n8n:5678",
        audit_ledger_path=str(ledger_path),
    )
    request = TriggerWorkflowRequest(webhook_id="run-demo", payload={"job": "sync", "run": 1})
    cache = IdempotencyCache(ttl_seconds=300)

    async with httpx.AsyncClient() as client:
        result = await trigger_n8n_workflow_impl(request, settings, client=client, cache=cache)

    records = read_jsonl(ledger_path)
    assert len(records) == 1
    assert records[0]["operation"] == "trigger_n8n_workflow"
    assert records[0]["request_id"] == result["request_id"]
    assert records[0]["request"]["webhook_id"] == "run-demo"
    assert records[0]["request"]["payload"] == {"job": "sync", "run": 1}
    assert records[0]["outcome"]["deduplicated"] is False
    assert records[0]["replay_fingerprint"] == build_replay_fingerprint(
        "trigger_n8n_workflow",
        {"webhook_id": "run-demo", "payload": {"job": "sync", "run": 1}},
    )


@pytest.mark.asyncio
@respx.mock
async def test_get_1password_secret_masks_secret_value_in_audit_ledger(tmp_path: Path) -> None:
    respx.get("http://1password-connect-api:8080/v1/vaults/vault-dev/items/item-001").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "item-001",
                "title": "Demo Secret",
                "fields": [
                    {"id": "api-key", "label": "api-key", "value": "super-secret"},
                ],
            },
        )
    )
    ledger_path = tmp_path / "audit-ledger.jsonl"
    settings = BridgeSettings(
        op_connect_url="http://1password-connect-api:8080",
        op_connect_token="development-token",
        audit_ledger_path=str(ledger_path),
    )
    request = SecretRequest(vault_id="vault-dev", item_id="item-001", field_label="api-key")

    async with httpx.AsyncClient() as client:
        result = await get_1password_secret_impl(request, settings, client=client)

    records = read_jsonl(ledger_path)
    serialized_records = ledger_path.read_text(encoding="utf-8")
    assert len(records) == 1
    assert records[0]["operation"] == "get_1password_secret"
    assert records[0]["request_id"] == result["request_id"]
    assert records[0]["request"]["vault_id"] == "vault-dev"
    assert records[0]["request"]["field_label"] == "api-key"
    assert records[0]["outcome"]["field_label"] == "api-key"
    assert records[0]["outcome"]["secret_value_redacted"] is True
    assert "super-secret" not in serialized_records
