from pathlib import Path


def test_production_artifacts_do_not_use_floating_image_references() -> None:
    compose = Path("/workspace/docker-compose.yml").read_text(encoding="utf-8")
    prod_env = Path("/workspace/.env.prod.example").read_text(encoding="utf-8")
    deployment = Path("/workspace/k8s/apps/zeroclaw-assistant/deployment.yaml").read_text(
        encoding="utf-8"
    )

    assert ":latest" not in compose
    assert ":latest" not in prod_env
    assert ":latest" not in deployment
    assert "imagePullPolicy: Always" not in deployment
    assert "OPENCLAW_IMAGE=ghcr.io/yourorg/openclaw@sha256:replace-with-published-image-digest" in prod_env
    assert "N8N_IMAGE=n8nio/n8n@sha256:replace-with-published-image-digest" in prod_env
    assert "image: ghcr.io/yourorg/zeroclaw-assistant@sha256:replace-with-published-image-digest" in deployment
