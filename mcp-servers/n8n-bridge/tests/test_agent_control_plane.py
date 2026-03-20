from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    AgentControlPlaneRequest,
    BridgeSettings,
    build_agent_control_plane_engine,
    build_replay_fingerprint,
    plan_agent_control_plane_impl,
)


def write_control_plane_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def base_control_plane_config() -> dict[str, object]:
    return {
        "version": 1,
        "quota_classes": {
            "standard": {
                "max_requests_per_minute": 60,
                "max_parallel_tasks": 2
            },
            "elevated": {
                "max_requests_per_minute": 240,
                "max_parallel_tasks": 8
            }
        },
        "tenants": {
            "tenant-a": {
                "allowed_capabilities": ["chat", "code", "memory"],
                "allowed_policy_packs": ["baseline", "strict"],
                "default_policy_pack": "baseline",
                "default_quota_class": "standard",
                "workspace_prefix": "tenant-a"
            },
            "tenant-b": {
                "allowed_capabilities": ["chat", "code", "memory", "workflow-admin"],
                "allowed_policy_packs": ["strict"],
                "default_policy_pack": "strict",
                "default_quota_class": "elevated",
                "workspace_prefix": "tenant-b"
            }
        }
    }


def test_agent_control_plane_assigns_default_policy_pack_and_quota(tmp_path: Path) -> None:
    settings = BridgeSettings(
        agent_control_plane_file_path=write_control_plane_config(
            tmp_path / "agent-control.json",
            base_control_plane_config(),
        )
    )
    engine = build_agent_control_plane_engine(settings)
    request = AgentControlPlaneRequest(
        tenant_id="tenant-a",
        agent_id="agent-001",
        requested_capabilities=["chat", "code"],
    )

    result = engine.plan(request)

    assert result["tenant_id"] == "tenant-a"
    assert result["policy_pack"] == "baseline"
    assert result["quota_class"] == "standard"
    assert result["workspace_id"] == "tenant-a-agent-001"


def test_agent_control_plane_honors_allowed_requested_policy_pack(tmp_path: Path) -> None:
    settings = BridgeSettings(
        agent_control_plane_file_path=write_control_plane_config(
            tmp_path / "agent-control.json",
            base_control_plane_config(),
        )
    )
    engine = build_agent_control_plane_engine(settings)
    request = AgentControlPlaneRequest(
        tenant_id="tenant-a",
        agent_id="agent-002",
        requested_capabilities=["memory"],
        requested_policy_pack="strict",
        requested_quota_class="standard",
    )

    result = engine.plan(request)

    assert result["policy_pack"] == "strict"
    assert result["quota_class"] == "standard"


def test_agent_control_plane_rejects_disallowed_capability(tmp_path: Path) -> None:
    settings = BridgeSettings(
        agent_control_plane_file_path=write_control_plane_config(
            tmp_path / "agent-control.json",
            base_control_plane_config(),
        )
    )
    engine = build_agent_control_plane_engine(settings)
    request = AgentControlPlaneRequest(
        tenant_id="tenant-a",
        agent_id="agent-003",
        requested_capabilities=["workflow-admin"],
    )

    with pytest.raises(RuntimeError, match="workflow-admin"):
        engine.plan(request)


def test_agent_control_plane_replay_fingerprint_is_deterministic(tmp_path: Path) -> None:
    settings = BridgeSettings(
        agent_control_plane_file_path=write_control_plane_config(
            tmp_path / "agent-control.json",
            base_control_plane_config(),
        )
    )
    engine = build_agent_control_plane_engine(settings)
    first_request = AgentControlPlaneRequest(
        tenant_id="tenant-b",
        agent_id="agent-004",
        requested_capabilities=["chat", "workflow-admin"],
        requested_quota_class="elevated",
    )
    second_request = AgentControlPlaneRequest(
        agent_id="agent-004",
        tenant_id="tenant-b",
        requested_quota_class="elevated",
        requested_capabilities=["chat", "workflow-admin"],
    )

    first = engine.plan(first_request)
    second = engine.plan(second_request)

    assert first["replay_fingerprint"] == second["replay_fingerprint"]
    assert first["replay_fingerprint"] == build_replay_fingerprint(
        "plan_agent_control_plane",
        first_request.model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_agent_control_plane_plan_returns_request_id(tmp_path: Path) -> None:
    settings = BridgeSettings(
        agent_control_plane_file_path=write_control_plane_config(
            tmp_path / "agent-control.json",
            base_control_plane_config(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = AgentControlPlaneRequest(
        tenant_id="tenant-b",
        agent_id="agent-005",
        requested_capabilities=["chat", "workflow-admin"],
        requested_quota_class="elevated",
    )

    result = await plan_agent_control_plane_impl(request, settings)

    assert result["request_id"]
    assert result["policy_pack"] == "strict"
