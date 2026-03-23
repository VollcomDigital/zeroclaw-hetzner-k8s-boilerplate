from __future__ import annotations

import ast
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_mcp_tool_names(server_source: str) -> list[str]:
    tree = ast.parse(server_source)

    def is_mcp_tool_decorator(dec: ast.expr) -> bool:
        func = dec
        if isinstance(dec, ast.Call):
            func = dec.func
        if not isinstance(func, ast.Attribute):
            return False
        if func.attr != "tool":
            return False
        return isinstance(func.value, ast.Name) and func.value.id == "MCP_SERVER"

    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if not any(is_mcp_tool_decorator(d) for d in node.decorator_list):
            continue
        names.append(node.name)

    return sorted(names)


def _policy_stems(policy_dir: Path) -> set[str]:
    stems: set[str] = set()
    for path in policy_dir.glob("*.json"):
        name = path.name
        for suffix in (".local.json", ".prod.json"):
            if name.endswith(suffix):
                stems.add(name[: -len(suffix)])
                break
        else:
            raise AssertionError(f"policy file must end with .local.json or .prod.json: {path}")
    return stems


def _planning_env_keys(planning_config_source: str) -> set[str]:
    return set(re.findall(r"\"(BRIDGE_[A-Z0-9_]+)\"", planning_config_source))


def test_mcp_control_plane_doc_exists_and_substantive() -> None:
    root = _repo_root()
    doc_path = root / "docs" / "mcp-control-plane.md"

    assert doc_path.is_file(), "expected docs/mcp-control-plane.md"
    body = doc_path.read_text(encoding="utf-8").strip()
    assert len(body) >= 400, "control-plane doc should carry operational detail"
    assert "#" in body


def test_readme_links_mcp_control_plane_doc() -> None:
    root = _repo_root()
    readme = (root / "README.md").read_text(encoding="utf-8")

    assert "docs/mcp-control-plane.md" in readme


def test_mcp_control_plane_doc_covers_each_registered_tool() -> None:
    root = _repo_root()
    server_py = root / "mcp-servers" / "n8n-bridge" / "src" / "n8n_bridge" / "server.py"
    doc_path = root / "docs" / "mcp-control-plane.md"
    tools = _iter_mcp_tool_names(server_py.read_text(encoding="utf-8"))
    doc = doc_path.read_text(encoding="utf-8")

    assert tools, "expected at least one MCP tool"
    for tool in tools:
        assert (
            f"`{tool}`" in doc
        ), f"doc must mention MCP tool `{tool}` (backticks, exact name)"


def test_mcp_control_plane_doc_covers_each_policy_stem() -> None:
    root = _repo_root()
    policy_dir = root / "infrastructure" / "policy"
    doc_path = root / "docs" / "mcp-control-plane.md"
    stems = _policy_stems(policy_dir)
    doc = doc_path.read_text(encoding="utf-8")

    assert stems, "expected policy JSON bundles"
    for stem in sorted(stems):
        prod = f"`infrastructure/policy/{stem}.prod.json`"
        local = f"`infrastructure/policy/{stem}.local.json`"
        assert prod in doc, f"doc must cite {prod}"
        assert local in doc, f"doc must cite {local}"


def test_mcp_control_plane_doc_lists_all_planning_config_env_keys() -> None:
    root = _repo_root()
    planning_py = root / "mcp-servers" / "n8n-bridge" / "src" / "n8n_bridge" / "planning_config.py"
    doc_path = root / "docs" / "mcp-control-plane.md"
    keys = _planning_env_keys(planning_py.read_text(encoding="utf-8"))
    doc = doc_path.read_text(encoding="utf-8")

    assert keys, "expected BRIDGE_* keys in planning_config.py"
    for key in sorted(keys):
        assert f"`{key}`" in doc, f"doc must mention env var `{key}`"


def test_policy_directory_has_expected_local_prod_pairs() -> None:
    root = _repo_root()
    policy_dir = root / "infrastructure" / "policy"
    stems = _policy_stems(policy_dir)

    for stem in stems:
        assert (policy_dir / f"{stem}.local.json").is_file()
        assert (policy_dir / f"{stem}.prod.json").is_file()


def test_mcp_tool_names_are_unique_and_non_empty() -> None:
    root = _repo_root()
    server_py = root / "mcp-servers" / "n8n-bridge" / "src" / "n8n_bridge" / "server.py"
    tools = _iter_mcp_tool_names(server_py.read_text(encoding="utf-8"))

    assert len(tools) == len(set(tools))
    for name in tools:
        assert name.isidentifier()
        assert len(name) >= 3
