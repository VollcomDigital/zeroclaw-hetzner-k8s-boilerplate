from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    BridgeSettings,
    ComplianceCaseRequest,
    build_compliance_platform_engine,
    build_replay_fingerprint,
    plan_compliance_case_impl,
)


def write_compliance_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def base_compliance_config() -> dict[str, object]:
    return {
        "version": 1,
        "regulations": {
            "gdpr": {
                "erase_targets": ["vector_memory", "workflow_history", "audit_ledger"],
                "evidence_requirements": ["decision_log", "retention_policy", "erase_report"],
                "default_residency": "eu"
            },
            "ai-act": {
                "erase_targets": [],
                "evidence_requirements": ["risk_register", "model_card", "decision_log"],
                "default_residency": "eu"
            }
        }
    }


def test_compliance_platform_plans_gdpr_erasure_targets(tmp_path: Path) -> None:
    settings = BridgeSettings(
        compliance_platform_config_path=write_compliance_config(
            tmp_path / "compliance.json",
            base_compliance_config(),
        )
    )
    engine = build_compliance_platform_engine(settings)
    request = ComplianceCaseRequest(
        regulation="gdpr",
        case_type="subject_erasure",
        subject_id="user-123",
        systems_affected=["audit_ledger", "vector_memory", "workflow_history"],
        data_classification="restricted",
        legal_hold=False,
    )

    result = engine.plan(request)

    assert result["action"] == "erase"
    assert result["erase_targets"] == ["audit_ledger", "vector_memory", "workflow_history"]
    assert result["residency_region"] == "eu"


def test_compliance_platform_legal_hold_blocks_erasure(tmp_path: Path) -> None:
    settings = BridgeSettings(
        compliance_platform_config_path=write_compliance_config(
            tmp_path / "compliance.json",
            base_compliance_config(),
        )
    )
    engine = build_compliance_platform_engine(settings)
    request = ComplianceCaseRequest(
        regulation="gdpr",
        case_type="subject_erasure",
        subject_id="user-123",
        systems_affected=["vector_memory"],
        data_classification="restricted",
        legal_hold=True,
    )

    result = engine.plan(request)

    assert result["action"] == "hold"
    assert result["erase_targets"] == []
    assert "legal hold" in " ".join(result["reasons"]).lower()


def test_compliance_platform_plans_audit_evidence_bundle(tmp_path: Path) -> None:
    settings = BridgeSettings(
        compliance_platform_config_path=write_compliance_config(
            tmp_path / "compliance.json",
            base_compliance_config(),
        )
    )
    engine = build_compliance_platform_engine(settings)
    request = ComplianceCaseRequest(
        regulation="ai-act",
        case_type="audit_evidence",
        subject_id="audit-req-001",
        systems_affected=["audit_ledger", "policy_engine"],
        data_classification="internal",
        legal_hold=False,
    )

    result = engine.plan(request)

    assert result["action"] == "collect_evidence"
    assert result["evidence_requirements"] == ["decision_log", "model_card", "risk_register"]
    assert result["evidence_bundle_id"]


def test_compliance_platform_replay_fingerprint_is_deterministic(tmp_path: Path) -> None:
    settings = BridgeSettings(
        compliance_platform_config_path=write_compliance_config(
            tmp_path / "compliance.json",
            base_compliance_config(),
        )
    )
    engine = build_compliance_platform_engine(settings)
    first_request = ComplianceCaseRequest(
        regulation="gdpr",
        case_type="subject_erasure",
        subject_id="user-123",
        systems_affected=["workflow_history", "vector_memory"],
        data_classification="restricted",
        legal_hold=False,
    )
    second_request = ComplianceCaseRequest(
        subject_id="user-123",
        legal_hold=False,
        data_classification="restricted",
        systems_affected=["vector_memory", "workflow_history"],
        regulation="gdpr",
        case_type="subject_erasure",
    )

    first = engine.plan(first_request)
    second = engine.plan(second_request)

    assert first["replay_fingerprint"] == second["replay_fingerprint"]
    assert first["replay_fingerprint"] == build_replay_fingerprint(
        "plan_compliance_case",
        first_request.model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_compliance_platform_plan_returns_request_id(tmp_path: Path) -> None:
    settings = BridgeSettings(
        compliance_platform_config_path=write_compliance_config(
            tmp_path / "compliance.json",
            base_compliance_config(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = ComplianceCaseRequest(
        regulation="gdpr",
        case_type="audit_evidence",
        subject_id="audit-req-002",
        systems_affected=["audit_ledger"],
        data_classification="internal",
        legal_hold=False,
    )

    result = await plan_compliance_case_impl(request, settings)

    assert result["request_id"]
    assert result["action"] == "collect_evidence"
