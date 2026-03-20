from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    BridgeSettings,
    SovereigntyRequest,
    build_replay_fingerprint,
    build_sovereignty_engine,
    plan_sovereignty_mode_impl,
)


def write_sovereignty_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def base_sovereignty_config() -> dict[str, object]:
    return {
        "version": 1,
        "rules": {
            "public": {
                "mode": "cross_boundary_allowed",
                "allowed_regions": ["*"]
            },
            "internal": {
                "mode": "in_region",
                "allowed_regions": ["eu", "eu-central"]
            },
            "restricted": {
                "mode": "local_only",
                "allowed_regions": ["local"]
            }
        }
    }


def test_sovereignty_mode_returns_local_only_for_restricted_data(tmp_path: Path) -> None:
    settings = BridgeSettings(
        sovereignty_file_path=write_sovereignty_config(
            tmp_path / "sovereignty.json",
            base_sovereignty_config(),
        )
    )
    engine = build_sovereignty_engine(settings)
    request = SovereigntyRequest(
        data_classification="restricted",
        source_region="eu-central",
        target_region="us-east",
        requires_local_processing=False,
    )

    result = engine.plan(request)

    assert result["mode"] == "local_only"
    assert result["allowed"] is False


def test_sovereignty_mode_allows_in_region_processing_for_internal_data(tmp_path: Path) -> None:
    settings = BridgeSettings(
        sovereignty_file_path=write_sovereignty_config(
            tmp_path / "sovereignty.json",
            base_sovereignty_config(),
        )
    )
    engine = build_sovereignty_engine(settings)
    request = SovereigntyRequest(
        data_classification="internal",
        source_region="eu-central",
        target_region="eu",
        requires_local_processing=False,
    )

    result = engine.plan(request)

    assert result["mode"] == "in_region"
    assert result["allowed"] is True


def test_sovereignty_mode_respects_explicit_locality_requirement(tmp_path: Path) -> None:
    settings = BridgeSettings(
        sovereignty_file_path=write_sovereignty_config(
            tmp_path / "sovereignty.json",
            base_sovereignty_config(),
        )
    )
    engine = build_sovereignty_engine(settings)
    request = SovereigntyRequest(
        data_classification="public",
        source_region="eu-central",
        target_region="eu",
        requires_local_processing=True,
    )

    result = engine.plan(request)

    assert result["mode"] == "local_only"
    assert result["allowed"] is False


def test_sovereignty_mode_replay_fingerprint_is_deterministic(tmp_path: Path) -> None:
    settings = BridgeSettings(
        sovereignty_file_path=write_sovereignty_config(
            tmp_path / "sovereignty.json",
            base_sovereignty_config(),
        )
    )
    engine = build_sovereignty_engine(settings)
    first_request = SovereigntyRequest(
        data_classification="internal",
        source_region="eu-central",
        target_region="eu",
        requires_local_processing=False,
    )
    second_request = SovereigntyRequest(
        target_region="eu",
        source_region="eu-central",
        requires_local_processing=False,
        data_classification="internal",
    )

    first = engine.plan(first_request)
    second = engine.plan(second_request)

    assert first["replay_fingerprint"] == second["replay_fingerprint"]
    assert first["replay_fingerprint"] == build_replay_fingerprint(
        "plan_sovereignty_mode",
        first_request.model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_sovereignty_mode_plan_returns_request_id(tmp_path: Path) -> None:
    settings = BridgeSettings(
        sovereignty_file_path=write_sovereignty_config(
            tmp_path / "sovereignty.json",
            base_sovereignty_config(),
        ),
        audit_ledger_path=str(tmp_path / "audit-ledger.jsonl"),
    )
    request = SovereigntyRequest(
        data_classification="public",
        source_region="eu-central",
        target_region="us-east",
        requires_local_processing=False,
    )

    result = await plan_sovereignty_mode_impl(request, settings)

    assert result["request_id"]
    assert result["mode"] == "cross_boundary_allowed"
