from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_release_architecture_index_exists_and_is_substantive() -> None:
    root = _repo_root()
    doc = root / "docs" / "architecture.md"

    assert doc.is_file()
    text = doc.read_text(encoding="utf-8")
    assert "\x00" not in text
    assert len(text.strip()) >= 1200


def test_readme_links_release_architecture_index() -> None:
    readme = (_repo_root() / "README.md").read_text(encoding="utf-8")

    assert "docs/architecture.md" in readme


def test_architecture_index_anchors_runtime_and_docs() -> None:
    text = (_repo_root() / "docs" / "architecture.md").read_text(encoding="utf-8")

    required = (
        "`docker-compose.yml`",
        "`docker-compose.local.yml`",
        "`mcp-control-plane.md`",
    )
    for token in required:
        assert token in text, f"architecture index must cite {token}"


def test_architecture_index_covers_compose_services_and_network_tiers() -> None:
    text = (_repo_root() / "docs" / "architecture.md").read_text(encoding="utf-8")

    for name in (
        "`traefik`",
        "`mcp-server-n8n`",
        "`alloy`",
        "`proxy-tier`",
        "`app-tier`",
        "`db-tier`",
        "`ai-tier`",
    ):
        assert name in text, f"architecture index must mention compose entity {name}"


def test_architecture_index_defines_release_review_headings() -> None:
    text = (_repo_root() / "docs" / "architecture.md").read_text(encoding="utf-8")

    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert len(headings) >= 6
    joined = "\n".join(headings)
    assert "Runtime" in joined or "topology" in joined.lower()
    assert "Security" in joined or "security" in joined.lower()
    assert "Observability" in joined or "observability" in joined.lower()


def test_architecture_index_includes_data_and_config_boundaries() -> None:
    text = (_repo_root() / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "`infrastructure/policy/`" in text
    assert ".env.prod.example" in text or "`PROD`" in text or "production" in text.lower()


def test_architecture_index_states_compose_as_canonical_runtime() -> None:
    text = (_repo_root() / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "Primary runtime" in text or "primary runtime" in text.lower()
    assert "runtime source of truth" in text.lower()
    assert "Docker Compose" in text or "`docker-compose.yml`" in text
