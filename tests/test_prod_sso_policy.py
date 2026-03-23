from pathlib import Path


def test_prod_sso_configuration_requires_explicit_entra_policy() -> None:
    compose = Path("/workspace/docker-compose.yml").read_text(encoding="utf-8")
    oauth2_proxy_cfg = Path("/workspace/infrastructure/sso/oauth2-proxy.cfg").read_text(
        encoding="utf-8"
    )
    env_example = Path("/workspace/.env.prod.example").read_text(encoding="utf-8")

    assert "OAUTH2_PROXY_EMAIL_DOMAINS: ${ENTRA_ALLOWED_EMAIL_DOMAINS:?" in compose
    assert "OAUTH2_PROXY_ALLOWED_GROUPS: ${ENTRA_ALLOWED_GROUPS:?" in compose
    assert 'email_domains = ["*"]' not in oauth2_proxy_cfg
    assert "ENTRA_ALLOWED_GROUPS=replace-with-entra-group-object-id" in env_example
    assert "ENTRA_ALLOWED_EMAIL_DOMAINS=example.com" in env_example
