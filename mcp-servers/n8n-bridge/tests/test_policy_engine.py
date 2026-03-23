from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from n8n_bridge.server import (
    BridgeSettings,
    PolicyDeniedError,
    SecretRequest,
    TriggerWorkflowRequest,
    build_policy_engine,
    get_1password_secret_impl,
    trigger_n8n_workflow_impl,
    IdempotencyCache,
)


def write_policy(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_policy_engine_allows_explicit_workflow_and_secret_scope(tmp_path: Path) -> None:
    settings = BridgeSettings(
        mcp_policy_config_path=write_policy(
            tmp_path / "policy.json",
            {
                "version": 1,
                "default_action": "deny",
                "tools": {
                    "trigger_n8n_workflow": {"allowed_webhook_ids": ["workflow-allowed"]},
                    "get_1password_secret": {
                        "allowed_vault_ids": ["vault-allowed"],
                        "allowed_item_ids": ["item-allowed"],
                        "allowed_field_labels": ["api-key"],
                    },
                },
            },
        )
    )

    policy = build_policy_engine(settings)

    workflow_decision = policy.authorize(
        "trigger_n8n_workflow",
        {"webhook_id": "workflow-allowed"},
    )
    secret_decision = policy.authorize(
        "get_1password_secret",
        {"vault_id": "vault-allowed", "item_id": "item-allowed", "field_label": "api-key"},
    )

    assert workflow_decision["allowed"] is True
    assert secret_decision["allowed"] is True


@pytest.mark.asyncio
@respx.mock
async def test_trigger_n8n_workflow_denies_disallowed_webhook(tmp_path: Path) -> None:
    settings = BridgeSettings(
        n8n_base_url="http://n8n:5678",
        mcp_policy_config_path=write_policy(
            tmp_path / "policy.json",
            {
                "version": 1,
                "default_action": "deny",
                "tools": {
                    "trigger_n8n_workflow": {"allowed_webhook_ids": ["workflow-allowed"]},
                },
            },
        ),
    )
    request = TriggerWorkflowRequest(webhook_id="workflow-blocked", payload={"job": "sync"})
    cache = IdempotencyCache(ttl_seconds=300)

    async with httpx.AsyncClient() as client:
        with pytest.raises(PolicyDeniedError, match="workflow-blocked"):
            await trigger_n8n_workflow_impl(request, settings, client=client, cache=cache)


@pytest.mark.asyncio
@respx.mock
async def test_get_1password_secret_denies_disallowed_field_scope(tmp_path: Path) -> None:
    settings = BridgeSettings(
        op_connect_url="http://1password-connect-api:8080",
        op_connect_token="development-token",
        mcp_policy_config_path=write_policy(
            tmp_path / "policy.json",
            {
                "version": 1,
                "default_action": "deny",
                "tools": {
                    "get_1password_secret": {
                        "allowed_vault_ids": ["vault-allowed"],
                        "allowed_item_ids": ["item-allowed"],
                        "allowed_field_labels": ["username"],
                    },
                },
            },
        ),
    )
    request = SecretRequest(vault_id="vault-allowed", item_id="item-allowed", field_label="api-key")

    async with httpx.AsyncClient() as client:
        with pytest.raises(PolicyDeniedError, match="api-key"):
            await get_1password_secret_impl(request, settings, client=client)
