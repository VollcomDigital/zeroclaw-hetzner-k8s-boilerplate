from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    AutonomousOptimizationRequest,
    BridgeSettings,
    build_autonomous_optimization_engine,
    build_replay_fingerprint,
    plan_autonomous_optimization_impl,
)


def write_optimization_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def base_optimization_config() -> dict[str, object]:
    return {
        "version": 1,
        "targets": {
            "latency_sensitive": {
                "max_p95_latency_ms": 1200,
                "max_error_rate": 0.02,
                "max_cost_per_1k_tokens_usd": 0.02
            }
        },
        "routes": {
            "local_vllm": {
                "current_p95_latency_ms": 1500,
                "current_error_rate": 0.01,
                "current_cost_per_1k_tokens_usd": 0.002,
                "recommended_priority_delta": 5
            },
            "remote_secure": {
                "current_p95_latency_ms": 900,
                "current_error_rate": 0.01,
                "current_cost_per_1k_tokens_usd": 0.03,
                "recommended_priority_delta": -5
            }
        }
    }


def test_autonomous_optimization_recommends_failover_for_latency_regression(tmp_path: Path) -> None:
    settings = BridgeSettings(
        autonomous_optimization_file_path=write_optimization_config(
            tmp_path / "optimization.json",
            base_optimization_config(),
        )
    )
    engine = build_autonomous_optimization_engine(settings)
    request = AutonomousOptimizationRequest(
        objective_key="latency_sensitive",
        route_name="local_vllm",
        subject_scope="tenant-a",
    )

    result = engine.plan(request)

    assert result["action"] == "deprioritize_route"
    assert result["recommended_priority_delta"] == 5
    assert "latency" in " ".join(result["reasons"]).lower()


def test_autonomous_optimization_recommends_cost_cap_for_expensive_route(tmp_path: Path) -> None:
    settings = BridgeSettings(
        autonomous_optimization_file_path=write_optimization_config(
            tmp_path / "optimization.json",
            base_optimization_config(),
        )
    )
    engine = build_autonomous_optimization_engine(settings)
    request = AutonomousOptimizationRequest(
        objective_key="latency_sensitive",
        route_name="remote_secure",
        subject_scope="tenant-a",
    )

    result = engine.plan(request)

    assert result["action"] == "cap_route_budget"
    assert result["recommended_priority_delta"] == -5
    assert result["budget_adjustment_required"] is True


def test_autonomous_optimization_replay_fingerprint_is_deterministic(tmp_path: Path) -> None:
    settings = BridgeSettings(
        autonomous_optimization_file_path=write_optimization_config(
            tmp_path / "optimization.json",
            base_optimization_config(),
        )
    )
    engine = build_autonomous_optimization_engine(settings)
    first_request = AutonomousOptimizationRequest(
        objective_key="latency_sensitive",
        route_name="local_vllm",
        subject_scope="tenant-a",
    )
    second_request = AutonomousOptimizationRequest(
        route_name="local_vllm",
        subject_scope="tenant-a",
        objective_key="latency_sensitive",
    )

    first = engine.plan(first_request)
    second = engine.plan(second_request)

    assert first["replay_fingerprint"] == second["replay_fingerprint"]
    assert first["replay_fingerprint"] == build_replay_fingerprint(
        "plan_autonomous_optimization",
        first_request.model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_autonomous_optimization_plan_returns_request_id(tmp_path: Path) -> None:
    settings = BridgeSettings(
        autonomous_optimization_file_path=write_optimization_config(
            tmp_path / "optimization.json",
            base_optimization_config(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = AutonomousOptimizationRequest(
        objective_key="latency_sensitive",
        route_name="remote_secure",
        subject_scope="tenant-a",
    )

    result = await plan_autonomous_optimization_impl(request, settings)

    assert result["request_id"]
    assert result["action"] == "cap_route_budget"
