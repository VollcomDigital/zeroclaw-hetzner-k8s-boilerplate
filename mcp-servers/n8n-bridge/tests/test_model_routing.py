from __future__ import annotations

import json
from pathlib import Path

import pytest

from n8n_bridge.server import (
    BridgeSettings,
    ModelRoutingRequest,
    build_model_router,
    build_replay_fingerprint,
)


def write_routing_config(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_model_router_prefers_low_latency_local_route_for_internal_requests(tmp_path: Path) -> None:
    settings = BridgeSettings(
        model_routing_config_path=write_routing_config(
            tmp_path / "routing.json",
            {
                "version": 1,
                "default_route": "remote_secure",
                "routes": {
                    "local_vllm": {
                        "base_url": "http://vllm:8000/v1",
                        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                        "provider": "vllm",
                        "capabilities": ["chat", "code"],
                        "allowed_data_classifications": ["public", "internal"],
                        "regions": ["local", "eu-central"],
                        "max_latency_ms": 800,
                        "priority": 10,
                        "requires_local": True,
                        "healthy": True,
                    },
                    "remote_secure": {
                        "base_url": "https://secure-llm.example.com/v1",
                        "model": "gpt-secure",
                        "provider": "remote",
                        "capabilities": ["chat", "code"],
                        "allowed_data_classifications": ["public", "internal", "restricted"],
                        "regions": ["*"],
                        "max_latency_ms": 3500,
                        "priority": 50,
                        "requires_local": False,
                        "healthy": True,
                    },
                },
            },
        )
    )
    router = build_model_router(settings)
    request = ModelRoutingRequest(
        workload_kind="code",
        data_classification="internal",
        max_latency_ms=1200,
        require_local=False,
        preferred_region="eu-central",
    )

    result = router.select_route(request)

    assert result["route_name"] == "local_vllm"
    assert result["provider"] == "vllm"
    assert result["base_url"] == "http://vllm:8000/v1"


def test_model_router_routes_restricted_data_to_secure_remote(tmp_path: Path) -> None:
    settings = BridgeSettings(
        model_routing_config_path=write_routing_config(
            tmp_path / "routing.json",
            {
                "version": 1,
                "default_route": "remote_secure",
                "routes": {
                    "local_vllm": {
                        "base_url": "http://vllm:8000/v1",
                        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                        "provider": "vllm",
                        "capabilities": ["chat", "code"],
                        "allowed_data_classifications": ["public", "internal"],
                        "regions": ["local"],
                        "max_latency_ms": 800,
                        "priority": 10,
                        "requires_local": True,
                        "healthy": True,
                    },
                    "remote_secure": {
                        "base_url": "https://secure-llm.example.com/v1",
                        "model": "gpt-secure",
                        "provider": "remote",
                        "capabilities": ["chat", "code"],
                        "allowed_data_classifications": ["public", "internal", "restricted"],
                        "regions": ["*"],
                        "max_latency_ms": 3500,
                        "priority": 50,
                        "requires_local": False,
                        "healthy": True,
                    },
                },
            },
        )
    )
    router = build_model_router(settings)
    request = ModelRoutingRequest(
        workload_kind="code",
        data_classification="restricted",
        max_latency_ms=4000,
        require_local=False,
        preferred_region="eu-central",
    )

    result = router.select_route(request)

    assert result["route_name"] == "remote_secure"
    assert result["provider"] == "remote"
    assert result["model"] == "gpt-secure"


def test_model_router_replay_fingerprint_is_deterministic(tmp_path: Path) -> None:
    settings = BridgeSettings(
        model_routing_config_path=write_routing_config(
            tmp_path / "routing.json",
            {
                "version": 1,
                "default_route": "remote_secure",
                "routes": {
                    "remote_secure": {
                        "base_url": "https://secure-llm.example.com/v1",
                        "model": "gpt-secure",
                        "provider": "remote",
                        "capabilities": ["chat"],
                        "allowed_data_classifications": ["public", "internal", "restricted"],
                        "regions": ["*"],
                        "max_latency_ms": 3500,
                        "priority": 50,
                        "requires_local": False,
                        "healthy": True,
                    }
                },
            },
        )
    )
    router = build_model_router(settings)
    first_request = ModelRoutingRequest(
        workload_kind="chat",
        data_classification="public",
        max_latency_ms=3000,
        require_local=False,
        preferred_region="eu-central",
    )
    second_request = ModelRoutingRequest(
        preferred_region="eu-central",
        require_local=False,
        max_latency_ms=3000,
        data_classification="public",
        workload_kind="chat",
    )

    first_result = router.select_route(first_request)
    second_result = router.select_route(second_request)

    assert first_result["replay_fingerprint"] == second_result["replay_fingerprint"]
    assert first_result["replay_fingerprint"] == build_replay_fingerprint(
        "select_model_route",
        first_request.model_dump(mode="json"),
    )


def test_model_router_raises_when_no_route_matches(tmp_path: Path) -> None:
    settings = BridgeSettings(
        model_routing_config_path=write_routing_config(
            tmp_path / "routing.json",
            {
                "version": 1,
                "default_route": None,
                "routes": {
                    "local_vllm": {
                        "base_url": "http://vllm:8000/v1",
                        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                        "provider": "vllm",
                        "capabilities": ["code"],
                        "allowed_data_classifications": ["public"],
                        "regions": ["local"],
                        "max_latency_ms": 500,
                        "priority": 10,
                        "requires_local": True,
                        "healthy": False,
                    }
                },
            },
        )
    )
    router = build_model_router(settings)
    request = ModelRoutingRequest(
        workload_kind="code",
        data_classification="restricted",
        max_latency_ms=200,
        require_local=True,
        preferred_region="eu-central",
    )

    with pytest.raises(RuntimeError, match="No healthy model route matched"):
        router.select_route(request)


def test_model_router_skips_gpu_route_when_utilization_exceeds_threshold(tmp_path: Path) -> None:
    settings = BridgeSettings(
        model_routing_config_path=write_routing_config(
            tmp_path / "routing.json",
            {
                "version": 1,
                "default_route": "remote_secure",
                "routes": {
                    "local_vllm": {
                        "base_url": "http://vllm:8000/v1",
                        "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
                        "provider": "vllm",
                        "capabilities": ["code"],
                        "allowed_data_classifications": ["public", "internal"],
                        "regions": ["local"],
                        "max_latency_ms": 600,
                        "priority": 10,
                        "requires_local": True,
                        "healthy": True,
                        "current_gpu_utilization_percent": 96,
                        "max_gpu_utilization_percent": 85
                    },
                    "remote_secure": {
                        "base_url": "https://secure-llm.example.com/v1",
                        "model": "gpt-secure",
                        "provider": "remote",
                        "capabilities": ["code"],
                        "allowed_data_classifications": ["public", "internal", "restricted"],
                        "regions": ["*"],
                        "max_latency_ms": 3500,
                        "priority": 50,
                        "requires_local": False,
                        "healthy": True
                    }
                }
            },
        )
    )
    router = build_model_router(settings)
    request = ModelRoutingRequest(
        workload_kind="code",
        data_classification="internal",
        max_latency_ms=4000,
        require_local=False,
        preferred_region="local",
    )

    result = router.select_route(request)

    assert result["route_name"] == "remote_secure"
    assert result["fallback"] is True


def test_model_router_skips_route_when_projected_cost_exceeds_budget(tmp_path: Path) -> None:
    settings = BridgeSettings(
        model_routing_config_path=write_routing_config(
            tmp_path / "routing.json",
            {
                "version": 1,
                "default_route": "budget_route",
                "routes": {
                    "budget_route": {
                        "base_url": "https://cheap-llm.example.com/v1",
                        "model": "cheap-model",
                        "provider": "remote",
                        "capabilities": ["chat"],
                        "allowed_data_classifications": ["public"],
                        "regions": ["*"],
                        "max_latency_ms": 2500,
                        "priority": 10,
                        "requires_local": False,
                        "healthy": True,
                        "estimated_cost_per_1k_tokens_usd": 0.20,
                        "daily_budget_usd": 10.0,
                        "current_spend_usd": 9.95
                    },
                    "fallback_route": {
                        "base_url": "https://fallback-llm.example.com/v1",
                        "model": "fallback-model",
                        "provider": "remote",
                        "capabilities": ["chat"],
                        "allowed_data_classifications": ["public"],
                        "regions": ["*"],
                        "max_latency_ms": 3500,
                        "priority": 50,
                        "requires_local": False,
                        "healthy": True,
                        "estimated_cost_per_1k_tokens_usd": 0.02
                    }
                }
            },
        )
    )
    router = build_model_router(settings)
    request = ModelRoutingRequest(
        workload_kind="chat",
        data_classification="public",
        max_latency_ms=4000,
        require_local=False,
        preferred_region="eu-central",
        estimated_total_tokens=500,
        max_cost_usd=0.10,
    )

    result = router.select_route(request)

    assert result["route_name"] == "fallback_route"
    assert result["projected_cost_usd"] == pytest.approx(0.01)
