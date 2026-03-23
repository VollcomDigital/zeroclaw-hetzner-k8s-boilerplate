"""Security workflow uses immutable action SHAs where required by policy."""

from __future__ import annotations

import re
from pathlib import Path


def _security_yml_text() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")


def test_gitleaks_action_is_pinned_to_commit_sha() -> None:
    text = _security_yml_text()
    assert re.search(r"uses:\s+gitleaks/gitleaks-action@[a-f0-9]{40}\b", text) is not None, (
        "gitleaks/gitleaks-action must use a full 40-char commit SHA (not a mutable tag)"
    )


def test_trivy_action_is_pinned_to_commit_sha() -> None:
    text = _security_yml_text()
    assert re.search(r"uses:\s+aquasecurity/trivy-action@[a-f0-9]{40}\b", text) is not None, (
        "aquasecurity/trivy-action must use a full 40-char commit SHA (not master or semver tag)"
    )
