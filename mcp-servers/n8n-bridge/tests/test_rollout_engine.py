from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    BridgeSettings,
    ProgressiveRolloutRequest,
    build_progressive_rollout_engine,
    plan_progressive_rollout_impl,
)


def write_rollout_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def base_rollout_config() -> dict[str, object]:
    return {
        "version": 1,
        "workflows": {
            "workflow-primary": {
                "mode": "shadow",
                "shadow_webhook_id": "workflow-shadow",
                "primary_webhook_id": "workflow-primary"
            },
            "workflow-canary": {
                "mode": "canary",
                "primary_webhook_id": "workflow-primary",
                "canary_webhook_id": "workflow-canary",
                "canary_percentage": 20
            }
        },
        "prompts": {
            "prompt-default": {
                "mode": "full",
                "active_prompt_version": "v2"
            },
            "prompt-canary": {
                "mode": "canary",
                "active_prompt_version": "v2",
                "canary_prompt_version": "v3",
                "canary_percentage": 10
            }
        }
    }


def test_rollout_engine_shadow_mode_routes_to_shadow_and_primary(tmp_path: Path) -> None:
    settings = BridgeSettings(
        progressive_rollout_config_path=write_rollout_config(tmp_path / "rollout.json", base_rollout_config())
    )
    engine = build_progressive_rollout_engine(settings)
    request = ProgressiveRolloutRequest(
        rollout_kind="workflow",
        rollout_key="workflow-primary",
        subject_id="tenant-a",
    )

    result = engine.plan(request)

    assert result["mode"] == "shadow"
    assert result["target"] == "workflow-primary"
    assert result["shadow_target"] == "workflow-shadow"


def test_rollout_engine_canary_is_deterministic_for_subject(tmp_path: Path) -> None:
    settings = BridgeSettings(
        progressive_rollout_config_path=write_rollout_config(tmp_path / "rollout.json", base_rollout_config())
    )
    engine = build_progressive_rollout_engine(settings)
    request = ProgressiveRolloutRequest(
        rollout_kind="workflow",
        rollout_key="workflow-canary",
        subject_id="tenant-sticky",
    )

    first = engine.plan(request)
    second = engine.plan(request)

    assert first["bucket"] == second["bucket"]
    assert first["target"] == second["target"]
    assert first["replay_fingerprint"] == second["replay_fingerprint"]


@pytest.mark.asyncio
async def test_rollout_engine_prompt_canary_records_prompt_versions(tmp_path: Path) -> None:
    settings = BridgeSettings(
        progressive_rollout_config_path=write_rollout_config(tmp_path / "rollout.json", base_rollout_config()),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = ProgressiveRolloutRequest(
        rollout_kind="prompt",
        rollout_key="prompt-canary",
        subject_id="user-123",
    )

    result = await plan_progressive_rollout_impl(request, settings)

    assert result["rollout_kind"] == "prompt"
    assert result["mode"] == "canary"
    assert result["target"]
    assert result["request_id"]


def test_rollout_engine_rejects_unknown_rollout_key(tmp_path: Path) -> None:
    settings = BridgeSettings(
        progressive_rollout_config_path=write_rollout_config(tmp_path / "rollout.json", base_rollout_config())
    )
    engine = build_progressive_rollout_engine(settings)
    request = ProgressiveRolloutRequest(
        rollout_kind="workflow",
        rollout_key="missing-rollout",
        subject_id="tenant-a",
    )

    with pytest.raises(RuntimeError, match="missing-rollout"):
        engine.plan(request)
