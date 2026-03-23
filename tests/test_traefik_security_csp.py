"""Regression tests for Traefik prod security middleware CSP strings."""

from __future__ import annotations

import re
from pathlib import Path


def _quoted_header_value(text: str, key: str) -> str:
    pattern = re.compile(rf"^\s*{re.escape(key)}:\s*\"(.*)\"\s*$", re.MULTILINE)
    match = pattern.search(text)
    assert match is not None, f"missing {key} in security.prod.yml"
    return match.group(1)


def test_security_prod_csp_enforced_disallows_inline_scripts() -> None:
    """Enforced policy uses script-src 'self' only; inline styles remain until UIs externalize CSS."""
    repo_root = Path(__file__).resolve().parents[1]
    raw = (repo_root / "infrastructure/traefik/dynamic/security.prod.yml").read_text(encoding="utf-8")
    enforced = _quoted_header_value(raw, "contentSecurityPolicy")
    assert "upgrade-insecure-requests" in enforced
    assert "script-src 'self' 'unsafe-inline'" not in enforced
    assert re.search(r"script-src\s+'self'(?:\s|;|$)", enforced) is not None
    assert "style-src 'self' 'unsafe-inline'" in enforced


def test_security_prod_omits_deprecated_browser_xss_filter_header() -> None:
    """Traefik browserXssFilter sets X-XSS-Protection; modern browsers deprecate it—rely on CSP instead."""
    repo_root = Path(__file__).resolve().parents[1]
    raw = (repo_root / "infrastructure/traefik/dynamic/security.prod.yml").read_text(encoding="utf-8")
    assert "browserXssFilter" not in raw


def test_security_prod_csp_report_only_stricter_than_enforced_for_style() -> None:
    """Report-Only drops style inline too so teams see violations before enforcing."""
    repo_root = Path(__file__).resolve().parents[1]
    raw = (repo_root / "infrastructure/traefik/dynamic/security.prod.yml").read_text(encoding="utf-8")
    report_only = _quoted_header_value(raw, "contentSecurityPolicyReportOnly")
    assert "upgrade-insecure-requests" in report_only
    assert "style-src 'self' 'unsafe-inline'" not in report_only
    assert "script-src 'self' 'unsafe-inline'" not in report_only
    assert re.search(r"script-src\s+'self'(?:\s|;|$)", report_only) is not None
    assert re.search(r"style-src\s+'self'(?:\s|;|$)", report_only) is not None
