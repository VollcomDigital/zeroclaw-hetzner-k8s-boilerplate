from pathlib import Path


def test_dependency_management_uses_repository_lockfiles() -> None:
    runtime_lock = Path("/workspace/mcp-servers/n8n-bridge/requirements.lock")
    dev_lock = Path("/workspace/mcp-servers/n8n-bridge/requirements-dev.lock")
    dockerfile = Path("/workspace/mcp-servers/n8n-bridge/Dockerfile").read_text(encoding="utf-8")
    ci_workflow = Path("/workspace/.github/workflows/ci.yml").read_text(encoding="utf-8")

    assert runtime_lock.exists()
    assert dev_lock.exists()

    runtime_content = runtime_lock.read_text(encoding="utf-8")
    dev_content = dev_lock.read_text(encoding="utf-8")

    assert "httpx==0.28.1" in runtime_content
    assert "mcp==1.26.0" in runtime_content
    assert "pydantic==2.12.5" in runtime_content
    assert "pytest==9.0.2" in dev_content
    assert "pytest-asyncio==1.3.0" in dev_content
    assert "respx==0.22.0" in dev_content
    assert "PyYAML==6.0.1" in dev_content

    assert "COPY requirements.lock /app/requirements.lock" in dockerfile
    assert "python -m pip install --requirement /app/requirements.lock" in dockerfile
    assert "python -m pip install --no-deps ." in dockerfile
    assert "python -m pip install ." not in dockerfile

    assert "python -m pip install --requirement ./mcp-servers/n8n-bridge/requirements-dev.lock" in ci_workflow
    assert "python -m pip install --no-deps -e ./mcp-servers/n8n-bridge" in ci_workflow
    assert 'python -m pip install -e "./mcp-servers/n8n-bridge[dev]" pyyaml' not in ci_workflow
