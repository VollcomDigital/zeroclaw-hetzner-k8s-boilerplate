from pathlib import Path


def test_ci_baseline_workflows_exist_and_cover_validation_security_and_updates() -> None:
    ci_workflow = Path("/workspace/.github/workflows/ci.yml")
    security_workflow = Path("/workspace/.github/workflows/security.yml")
    codeql_workflow = Path("/workspace/.github/workflows/codeql.yml")
    dependabot_config = Path("/workspace/.github/dependabot.yml")

    assert ci_workflow.exists()
    assert security_workflow.exists()
    assert codeql_workflow.exists()
    assert dependabot_config.exists()

    ci_content = ci_workflow.read_text(encoding="utf-8")
    security_content = security_workflow.read_text(encoding="utf-8")
    codeql_content = codeql_workflow.read_text(encoding="utf-8")
    dependabot_content = dependabot_config.read_text(encoding="utf-8")

    assert "make validate-prod" in ci_content
    assert "make validate-local-mac" in ci_content
    assert "make validate-local-windows" in ci_content
    assert "make validate-local-core" in ci_content
    assert "python -m pytest tests mcp-servers/n8n-bridge/tests -q" in ci_content
    assert "python -m py_compile mcp-servers/n8n-bridge/src/n8n_bridge/server.py" in ci_content

    assert "gitleaks" in security_content.lower()
    assert "trivy" in security_content.lower()
    assert "upload-sarif" in security_content

    assert "github/codeql-action/init@v3" in codeql_content
    assert "github/codeql-action/autobuild@v3" in codeql_content
    assert "github/codeql-action/analyze@v3" in codeql_content
    assert "github/codeql-action/analyze@v4" not in codeql_content
    assert "languages: python" in codeql_content
    assert "languages: javascript" not in codeql_content

    assert 'package-ecosystem: "github-actions"' in dependabot_content
    assert 'package-ecosystem: "pip"' in dependabot_content
    assert 'directory: "/mcp-servers/n8n-bridge"' in dependabot_content
