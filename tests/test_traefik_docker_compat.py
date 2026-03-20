from pathlib import Path


def test_traefik_uses_a_docker_29_compatible_release() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    local_compose = (repo_root / "docker-compose.local.yml").read_text(encoding="utf-8")
    prod_compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "image: traefik:v3.6.1" in local_compose
    assert "image: traefik:v3.6.1" in prod_compose
