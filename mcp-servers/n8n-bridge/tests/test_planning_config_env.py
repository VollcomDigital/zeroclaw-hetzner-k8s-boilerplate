from __future__ import annotations

from collections.abc import Generator

import pytest
from pydantic import ValidationError

from n8n_bridge.planning_config import (
    PLANNING_CONFIG_BINDINGS,
    PlanningConfigBinding,
    first_non_empty_env,
)
from n8n_bridge.server import BridgeSettings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    yield
    get_settings.cache_clear()


def test_first_non_empty_env_returns_first_meaningful_value() -> None:
    env = {"A": "  ", "B": "\t", "C": " /ok "}
    assert first_non_empty_env(env, "A", "B", "C") == "/ok"


def test_first_non_empty_env_returns_none_when_all_blank_or_missing() -> None:
    assert first_non_empty_env({"X": " "}, "A", "B") is None


@pytest.mark.parametrize(
    "binding",
    PLANNING_CONFIG_BINDINGS,
    ids=lambda b: b.settings_field,
)
def test_canonical_planning_env_wins_over_legacy(
    monkeypatch: pytest.MonkeyPatch,
    binding: PlanningConfigBinding,
) -> None:
    primary, legacy = binding.env_keys[0], binding.env_keys[1]
    monkeypatch.setenv(primary, "/canonical.json")
    monkeypatch.setenv(legacy, "/legacy.json")
    get_settings.cache_clear()

    resolved = getattr(get_settings(), binding.settings_field)
    assert resolved == "/canonical.json"


@pytest.mark.parametrize(
    "binding",
    PLANNING_CONFIG_BINDINGS,
    ids=lambda b: b.settings_field,
)
def test_legacy_planning_env_used_when_canonical_missing(
    monkeypatch: pytest.MonkeyPatch,
    binding: PlanningConfigBinding,
) -> None:
    primary, legacy = binding.env_keys[0], binding.env_keys[1]
    monkeypatch.delenv(primary, raising=False)
    monkeypatch.setenv(legacy, "/legacy-only.json")
    get_settings.cache_clear()

    resolved = getattr(get_settings(), binding.settings_field)
    assert resolved == "/legacy-only.json"


def test_whitespace_only_canonical_falls_through_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRIDGE_MCP_POLICY_CONFIG_PATH", "  \n")
    monkeypatch.setenv("BRIDGE_POLICY_FILE_PATH", "/fallback.json")
    get_settings.cache_clear()

    assert get_settings().mcp_policy_config_path == "/fallback.json"


def test_all_planning_env_keys_are_globally_unique() -> None:
    seen: set[str] = set()
    for binding in PLANNING_CONFIG_BINDINGS:
        for key in binding.env_keys:
            assert key not in seen, f"duplicate env key: {key}"
            seen.add(key)


def test_bridge_settings_defaults_all_planning_paths_none() -> None:
    settings = BridgeSettings()
    for binding in PLANNING_CONFIG_BINDINGS:
        assert getattr(settings, binding.settings_field) is None


@pytest.mark.parametrize(
    "binding",
    PLANNING_CONFIG_BINDINGS,
    ids=lambda b: b.settings_field,
)
def test_get_settings_yields_none_when_no_planning_env_set(
    monkeypatch: pytest.MonkeyPatch,
    binding: PlanningConfigBinding,
) -> None:
    for b in PLANNING_CONFIG_BINDINGS:
        for key in b.env_keys:
            monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()

    assert getattr(get_settings(), binding.settings_field) is None


def test_get_settings_invalid_mcp_port_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_PORT", "not-a-port")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()


def test_get_settings_invalid_request_timeout_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRIDGE_REQUEST_TIMEOUT_SECONDS", "not-a-float")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()


def test_get_settings_coerces_numeric_env_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_PORT", "9000")
    monkeypatch.setenv("BRIDGE_REQUEST_TIMEOUT_SECONDS", "30.5")
    monkeypatch.setenv("BRIDGE_IDEMPOTENCY_TTL_SECONDS", "120")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.port == 9000
    assert settings.request_timeout_seconds == 30.5
    assert settings.idempotency_ttl_seconds == 120.0
