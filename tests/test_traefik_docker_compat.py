from pathlib import Path


def test_traefik_uses_a_docker_29_compatible_release() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    local_compose = (repo_root / "docker-compose.local.yml").read_text(encoding="utf-8")
    prod_compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "image: traefik:v3.6.1" in local_compose
    assert "image: traefik:v3.6.1" in prod_compose

    assert "  browser:" in local_compose
    assert "  browser:" in prod_compose
    assert "http.server" in local_compose
    assert "http.server" in prod_compose

    assert "Host(`${OPENWORK_HOST:-openwork.localhost}`)" in local_compose
    assert "Host(`${OPENCLAW_HOST:-openclaw.localhost}`)" in local_compose
    assert "Host(`${N8N_HOST:-n8n.localhost}`)" in local_compose


def test_openclaw_entrypoint_script_is_lf_only_for_linux_bind_mount() -> None:
    """CRLF in bind-mounted shell scripts breaks `set -eu` in /bin/sh (Illegal option -)."""
    script = Path(__file__).resolve().parents[1] / "infrastructure/openclaw/entrypoint-docker.sh"
    data = script.read_bytes()
    assert b"\r" not in data, "entrypoint-docker.sh must use LF line endings only"
