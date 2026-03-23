"""Ensure the MCP n8n-bridge production image does not bake in test code."""

from __future__ import annotations

from pathlib import Path


def test_n8n_bridge_dockerfile_does_not_copy_tests_into_image() -> None:
    dockerfile = Path(__file__).resolve().parents[1] / "mcp-servers" / "n8n-bridge" / "Dockerfile"
    text = dockerfile.read_text(encoding="utf-8")
    assert "COPY tests" not in text


def test_n8n_bridge_dockerignore_excludes_tests_directory() -> None:
    ignore = Path(__file__).resolve().parents[1] / "mcp-servers" / "n8n-bridge" / ".dockerignore"
    assert ignore.is_file()
    assert "tests/" in ignore.read_text(encoding="utf-8")
