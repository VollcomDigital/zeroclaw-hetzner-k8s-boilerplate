"""Compose anchors: vendor-safe runtime vs hardened first-party stacks."""

from __future__ import annotations

from pathlib import Path


def test_prod_runtime_anchor_excludes_read_only_and_user() -> None:
    repo = Path(__file__).resolve().parents[1]
    text = (repo / "docker-compose.yml").read_text(encoding="utf-8")
    runtime_block = text.split("x-hardened-defaults:")[0].split("x-runtime-defaults:")[1]
    assert "read_only:" not in runtime_block
    assert "user:" not in runtime_block
    assert "mcp-server-n8n:" in text
    mcp = text.split("  mcp-server-n8n:")[1].split("  qdrant:")[0]
    assert "hardened_defaults" in mcp


def test_local_runtime_anchor_excludes_user_and_tmpfs() -> None:
    repo = Path(__file__).resolve().parents[1]
    text = (repo / "docker-compose.local.yml").read_text(encoding="utf-8")
    local_block = text.split("x-local-hardened:")[0].split("x-local-runtime:")[1]
    assert "user:" not in local_block
    assert "tmpfs:" not in local_block
    mcp = text.split("  mcp-server-n8n:")[1].split("  qdrant:")[0]
    assert "local_hardened" in mcp
