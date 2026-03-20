from pathlib import Path


def test_readme_defines_canonical_platform_narrative() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    assert "# hybrid-enterprise-ai-agent-stack" in readme
    assert "## Canonical Platform Narrative" in readme
    assert "Primary runtime: Docker Compose hybrid stack" in readme
    assert "Secondary reference deployment: Kubernetes ZeroClaw assistant" in readme
    assert "`docker-compose.yml`" in readme
    assert "`docker-compose.local.yml`" in readme
    assert "`k8s/apps/zeroclaw-assistant/`" in readme
