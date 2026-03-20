from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

__all__ = (
    "PlanningConfigBinding",
    "PLANNING_CONFIG_BINDINGS",
    "first_non_empty_env",
)


@dataclass(frozen=True, slots=True)
class PlanningConfigBinding:
    settings_field: str
    env_keys: tuple[str, ...]


def first_non_empty_env(environ: Mapping[str, str], *keys: str) -> str | None:
    for key in keys:
        raw = environ.get(key)
        if raw is None:
            continue
        stripped = raw.strip()
        if stripped:
            return stripped
    return None


PLANNING_CONFIG_BINDINGS: Final[tuple[PlanningConfigBinding, ...]] = (
    PlanningConfigBinding(
        "mcp_policy_config_path",
        ("BRIDGE_MCP_POLICY_CONFIG_PATH", "BRIDGE_POLICY_FILE_PATH"),
    ),
    PlanningConfigBinding(
        "model_routing_config_path",
        ("BRIDGE_MODEL_ROUTING_CONFIG_PATH", "BRIDGE_ROUTING_FILE_PATH"),
    ),
    PlanningConfigBinding(
        "vector_memory_config_path",
        ("BRIDGE_VECTOR_MEMORY_CONFIG_PATH", "BRIDGE_VECTOR_MEMORY_POLICY_FILE_PATH"),
    ),
    PlanningConfigBinding(
        "progressive_rollout_config_path",
        ("BRIDGE_PROGRESSIVE_ROLLOUT_CONFIG_PATH", "BRIDGE_ROLLOUT_FILE_PATH"),
    ),
    PlanningConfigBinding(
        "failure_mode_config_path",
        ("BRIDGE_FAILURE_MODE_CONFIG_PATH", "BRIDGE_FAILURE_MODE_FILE_PATH"),
    ),
    PlanningConfigBinding(
        "confidential_execution_config_path",
        (
            "BRIDGE_CONFIDENTIAL_EXECUTION_CONFIG_PATH",
            "BRIDGE_CONFIDENTIAL_EXECUTION_FILE_PATH",
        ),
    ),
    PlanningConfigBinding(
        "agent_control_plane_config_path",
        ("BRIDGE_AGENT_CONTROL_PLANE_CONFIG_PATH", "BRIDGE_AGENT_CONTROL_PLANE_FILE_PATH"),
    ),
    PlanningConfigBinding(
        "compliance_platform_config_path",
        ("BRIDGE_COMPLIANCE_PLATFORM_CONFIG_PATH", "BRIDGE_COMPLIANCE_PLATFORM_FILE_PATH"),
    ),
    PlanningConfigBinding(
        "autonomous_optimization_config_path",
        (
            "BRIDGE_AUTONOMOUS_OPTIMIZATION_CONFIG_PATH",
            "BRIDGE_AUTONOMOUS_OPTIMIZATION_FILE_PATH",
        ),
    ),
    PlanningConfigBinding(
        "sovereignty_config_path",
        ("BRIDGE_SOVEREIGNTY_CONFIG_PATH", "BRIDGE_SOVEREIGNTY_FILE_PATH"),
    ),
)
