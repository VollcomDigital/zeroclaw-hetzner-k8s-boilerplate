from pathlib import Path


def test_integration_test_matrix_is_wired_into_ci() -> None:
    integration_suite = Path("/workspace/mcp-servers/n8n-bridge/tests/test_integration_matrix.py")
    ci_workflow = Path("/workspace/.github/workflows/ci.yml").read_text(encoding="utf-8")

    assert integration_suite.exists()
    assert "integration-matrix:" in ci_workflow
    assert "strategy:" in ci_workflow
    assert "scenario: [toolchain, idempotency]" in ci_workflow
    assert "python -m pytest mcp-servers/n8n-bridge/tests/test_integration_matrix.py -q" in ci_workflow
