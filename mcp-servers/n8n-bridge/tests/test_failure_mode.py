from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    BridgeSettings,
    FailureModeRequest,
    build_failure_mode_engine,
    plan_failure_mode_impl,
)


def write_failure_mode_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def base_failure_mode_config() -> dict[str, object]:
    return {
        "version": 1,
        "default_action": "degrade",
        "rules": {
            "model_router:upstream_timeout": {
                "action": "failover",
                "max_retries": 1,
                "fallback_target": "remote_secure"
            },
            "n8n:upstream_timeout": {
                "action": "retry",
                "max_retries": 2,
                "backoff_seconds": [1, 5, 15]
            },
            "1password:auth_error": {
                "action": "halt",
                "max_retries": 0
            }
        }
    }


def test_failure_mode_engine_selects_retry_for_transient_upstream_issue(tmp_path: Path) -> None:
    settings = BridgeSettings(
        failure_mode_config_path=write_failure_mode_config(
            tmp_path / "failure-mode.json",
            base_failure_mode_config(),
        )
    )
    engine = build_failure_mode_engine(settings)
    request = FailureModeRequest(
        component_name="n8n",
        failure_type="upstream_timeout",
        severity="high",
        retry_count=0,
        data_classification="internal",
    )

    result = engine.plan(request)

    assert result["action"] == "retry"
    assert result["retry_allowed"] is True
    assert result["next_backoff_seconds"] == 1


def test_failure_mode_engine_selects_failover_for_model_route_outage(tmp_path: Path) -> None:
    settings = BridgeSettings(
        failure_mode_config_path=write_failure_mode_config(
            tmp_path / "failure-mode.json",
            base_failure_mode_config(),
        )
    )
    engine = build_failure_mode_engine(settings)
    request = FailureModeRequest(
        component_name="model_router",
        failure_type="upstream_timeout",
        severity="critical",
        retry_count=1,
        data_classification="internal",
    )

    result = engine.plan(request)

    assert result["action"] == "failover"
    assert result["fallback_target"] == "remote_secure"
    assert result["retry_allowed"] is False


def test_failure_mode_engine_halts_on_secret_auth_error(tmp_path: Path) -> None:
    settings = BridgeSettings(
        failure_mode_config_path=write_failure_mode_config(
            tmp_path / "failure-mode.json",
            base_failure_mode_config(),
        )
    )
    engine = build_failure_mode_engine(settings)
    request = FailureModeRequest(
        component_name="1password",
        failure_type="auth_error",
        severity="critical",
        retry_count=0,
        data_classification="restricted",
    )

    result = engine.plan(request)

    assert result["action"] == "halt"
    assert result["retry_allowed"] is False


@pytest.mark.asyncio
async def test_failure_mode_plan_records_request_id_and_action(tmp_path: Path) -> None:
    settings = BridgeSettings(
        failure_mode_config_path=write_failure_mode_config(
            tmp_path / "failure-mode.json",
            base_failure_mode_config(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = FailureModeRequest(
        component_name="n8n",
        failure_type="upstream_timeout",
        severity="high",
        retry_count=1,
        data_classification="internal",
    )

    result = await plan_failure_mode_impl(request, settings)

    assert result["request_id"]
    assert result["action"] == "retry"
    assert result["replay_fingerprint"]
