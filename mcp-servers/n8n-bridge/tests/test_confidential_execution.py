from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    BridgeSettings,
    ConfidentialExecutionRequest,
    build_confidential_execution_engine,
    build_replay_fingerprint,
    plan_confidential_execution_impl,
)


def write_confidential_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def base_confidential_config() -> dict[str, object]:
    return {
        "version": 1,
        "targets": {
            "attested_local_gpu": {
                "execution_mode": "attested-local",
                "provider": "nvidia-cc",
                "endpoint": "https://local-attested-gpu.example",
                "attested": True,
                "supports_gpu": True,
                "provides_workload_identity": True,
                "allowed_data_classifications": ["internal", "restricted"],
                "regions": ["local", "eu-central"],
                "priority": 10,
                "healthy": True
            },
            "attested_remote_cpu": {
                "execution_mode": "attested-remote",
                "provider": "trusted-tee",
                "endpoint": "https://attested-remote.example",
                "attested": True,
                "supports_gpu": False,
                "provides_workload_identity": True,
                "allowed_data_classifications": ["public", "internal", "restricted"],
                "regions": ["*"],
                "priority": 20,
                "healthy": True
            },
            "isolated_remote": {
                "execution_mode": "isolated-remote",
                "provider": "sandbox",
                "endpoint": "https://isolated-remote.example",
                "attested": False,
                "supports_gpu": False,
                "provides_workload_identity": False,
                "allowed_data_classifications": ["public", "internal"],
                "regions": ["*"],
                "priority": 50,
                "healthy": True
            }
        }
    }


def test_confidential_execution_prefers_attested_gpu_for_restricted_gpu_workload(tmp_path: Path) -> None:
    settings = BridgeSettings(
        confidential_execution_file_path=write_confidential_config(
            tmp_path / "confidential.json",
            base_confidential_config(),
        )
    )
    engine = build_confidential_execution_engine(settings)
    request = ConfidentialExecutionRequest(
        workload_kind="training",
        data_classification="restricted",
        requires_attestation=True,
        requires_gpu=True,
        requires_workload_identity=True,
        preferred_region="eu-central",
    )

    result = engine.plan(request)

    assert result["target_name"] == "attested_local_gpu"
    assert result["execution_mode"] == "attested-local"
    assert result["provider"] == "nvidia-cc"


def test_confidential_execution_rejects_targets_without_workload_identity(tmp_path: Path) -> None:
    settings = BridgeSettings(
        confidential_execution_file_path=write_confidential_config(
            tmp_path / "confidential.json",
            base_confidential_config(),
        )
    )
    engine = build_confidential_execution_engine(settings)
    request = ConfidentialExecutionRequest(
        workload_kind="chat",
        data_classification="internal",
        requires_attestation=False,
        requires_gpu=False,
        requires_workload_identity=True,
        preferred_region="eu-central",
    )

    result = engine.plan(request)

    assert result["target_name"] != "isolated_remote"
    assert result["provides_workload_identity"] is True


def test_confidential_execution_replay_fingerprint_is_deterministic(tmp_path: Path) -> None:
    settings = BridgeSettings(
        confidential_execution_file_path=write_confidential_config(
            tmp_path / "confidential.json",
            base_confidential_config(),
        )
    )
    engine = build_confidential_execution_engine(settings)
    first_request = ConfidentialExecutionRequest(
        workload_kind="chat",
        data_classification="internal",
        requires_attestation=True,
        requires_gpu=False,
        requires_workload_identity=True,
        preferred_region="eu-central",
    )
    second_request = ConfidentialExecutionRequest(
        preferred_region="eu-central",
        requires_workload_identity=True,
        requires_gpu=False,
        requires_attestation=True,
        data_classification="internal",
        workload_kind="chat",
    )

    first = engine.plan(first_request)
    second = engine.plan(second_request)

    assert first["replay_fingerprint"] == second["replay_fingerprint"]
    assert first["replay_fingerprint"] == build_replay_fingerprint(
        "plan_confidential_execution",
        first_request.model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_confidential_execution_plan_returns_request_id(tmp_path: Path) -> None:
    settings = BridgeSettings(
        confidential_execution_file_path=write_confidential_config(
            tmp_path / "confidential.json",
            base_confidential_config(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = ConfidentialExecutionRequest(
        workload_kind="chat",
        data_classification="internal",
        requires_attestation=True,
        requires_gpu=False,
        requires_workload_identity=True,
        preferred_region="eu-central",
    )

    result = await plan_confidential_execution_impl(request, settings)

    assert result["request_id"]
    assert result["target_name"] == "attested_remote_cpu"
