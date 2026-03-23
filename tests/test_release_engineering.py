from pathlib import Path


def test_release_engineering_workflow_exists_and_publishes_immutable_artifacts() -> None:
    workflow = Path("/workspace/.github/workflows/release.yml")
    assert workflow.exists()

    content = workflow.read_text(encoding="utf-8")

    assert 'workflow_dispatch:' in content
    assert 'tags:' in content
    assert "- 'v*'" in content
    assert 'docker/metadata-action@v5' in content
    assert 'docker/login-action@v3' in content
    assert 'docker/build-push-action@v6' in content
    assert 'ghcr.io/${{ github.repository_owner }}/mcp-n8n-bridge' in content
    assert 'sbom: true' in content
    assert 'provenance: mode=max' in content
    assert 'python -m build --sdist --wheel --outdir dist ./mcp-servers/n8n-bridge' in content
    assert 'actions/upload-artifact@v4' in content
    assert 'release-manifest.json' in content
