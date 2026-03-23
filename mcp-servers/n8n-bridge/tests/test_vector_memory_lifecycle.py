from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    BridgeSettings,
    VectorMemoryLifecycleRequest,
    build_replay_fingerprint,
    build_vector_memory_lifecycle_engine,
    plan_vector_memory_lifecycle_impl,
)


def write_vector_policy(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def default_policy_payload() -> dict[str, object]:
    return {
        "version": 1,
        "default_action": "retain",
        "classification_rules": {
            "public": {"retention_days": 30, "expiry_action": "delete"},
            "internal": {"retention_days": 14, "expiry_action": "delete"},
            "restricted": {"retention_days": 7, "expiry_action": "delete"},
        },
        "pii_overrides": {
            "email": {"retention_days": 3, "expiry_action": "delete"},
            "phone": {"retention_days": 3, "expiry_action": "delete"},
        },
    }


def test_vector_memory_lifecycle_replay_fingerprint_is_deterministic(tmp_path: Path) -> None:
    settings = BridgeSettings(
        vector_memory_config_path=write_vector_policy(
            tmp_path / "vector-policy.json",
            default_policy_payload(),
        )
    )
    first_request = VectorMemoryLifecycleRequest(
        memory_id="mem-001",
        subject_id="user-123",
        data_classification="internal",
        pii_labels=["email"],
        created_at="2026-03-01T00:00:00+00:00",
        last_accessed_at="2026-03-02T00:00:00+00:00",
    )
    second_request = VectorMemoryLifecycleRequest(
        subject_id="user-123",
        memory_id="mem-001",
        pii_labels=["email"],
        data_classification="internal",
        last_accessed_at="2026-03-02T00:00:00+00:00",
        created_at="2026-03-01T00:00:00+00:00",
    )

    first = build_replay_fingerprint("plan_vector_memory_lifecycle", first_request.model_dump(mode="json"))
    second = build_replay_fingerprint("plan_vector_memory_lifecycle", second_request.model_dump(mode="json"))

    assert first == second
    assert build_vector_memory_lifecycle_engine(settings)


def test_vector_memory_lifecycle_replay_fingerprint_ignores_pii_label_order(tmp_path: Path) -> None:
    write_vector_policy(
        tmp_path / "vector-policy.json",
        default_policy_payload(),
    )
    a = VectorMemoryLifecycleRequest(
        memory_id="mem-001",
        subject_id="user-123",
        data_classification="internal",
        pii_labels=["email", "phone"],
        created_at="2026-03-01T00:00:00+00:00",
    )
    b = VectorMemoryLifecycleRequest(
        memory_id="mem-001",
        subject_id="user-123",
        data_classification="internal",
        pii_labels=["phone", "email"],
        created_at="2026-03-01T00:00:00+00:00",
    )
    assert build_replay_fingerprint(
        "plan_vector_memory_lifecycle", a.model_dump(mode="json")
    ) == build_replay_fingerprint("plan_vector_memory_lifecycle", b.model_dump(mode="json"))


@pytest.mark.asyncio
async def test_vector_memory_lifecycle_respects_legal_hold_over_delete_request(tmp_path: Path) -> None:
    settings = BridgeSettings(
        vector_memory_config_path=write_vector_policy(
            tmp_path / "vector-policy.json",
            default_policy_payload(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = VectorMemoryLifecycleRequest(
        memory_id="mem-legal-hold",
        subject_id="user-123",
        data_classification="restricted",
        pii_labels=["email"],
        created_at="2026-03-01T00:00:00+00:00",
        deletion_requested=True,
        legal_hold=True,
    )

    result = await plan_vector_memory_lifecycle_impl(request, settings)

    assert result["action"] == "retain"
    assert result["delete_embeddings"] is False
    assert "legal hold" in " ".join(result["reasons"]).lower()


@pytest.mark.asyncio
async def test_vector_memory_lifecycle_deletes_expired_pii_memory(tmp_path: Path) -> None:
    settings = BridgeSettings(
        vector_memory_config_path=write_vector_policy(
            tmp_path / "vector-policy.json",
            default_policy_payload(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = VectorMemoryLifecycleRequest(
        memory_id="mem-expired",
        subject_id="user-456",
        data_classification="internal",
        pii_labels=["email"],
        created_at="2026-03-01T00:00:00+00:00",
        evaluation_time="2026-03-10T00:00:00+00:00",
    )

    result = await plan_vector_memory_lifecycle_impl(request, settings)

    assert result["action"] == "delete"
    assert result["delete_embeddings"] is True
    assert result["retention_days"] == 3


@pytest.mark.asyncio
async def test_vector_memory_lifecycle_retains_unexpired_non_pii_memory(tmp_path: Path) -> None:
    settings = BridgeSettings(
        vector_memory_config_path=write_vector_policy(
            tmp_path / "vector-policy.json",
            default_policy_payload(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = VectorMemoryLifecycleRequest(
        memory_id="mem-retain",
        subject_id="user-789",
        data_classification="public",
        pii_labels=[],
        created_at="2026-03-01T00:00:00+00:00",
        evaluation_time="2026-03-05T00:00:00+00:00",
    )

    result = await plan_vector_memory_lifecycle_impl(request, settings)

    assert result["action"] == "retain"
    assert result["delete_embeddings"] is False
    assert result["retention_days"] == 30
