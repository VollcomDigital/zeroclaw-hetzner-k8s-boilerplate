"""Production stack must pull the MCP n8n bridge from a registry, not build on the host."""

from __future__ import annotations

from pathlib import Path


def test_prod_compose_mcp_server_n8n_uses_registry_image_not_build() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    text = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")
    start = text.index("  mcp-server-n8n:")
    end = text.index("  qdrant:", start)
    section = text[start:end]
    assert "build:" not in section
    assert "image: ${MCP_N8N_BRIDGE_IMAGE" in section
