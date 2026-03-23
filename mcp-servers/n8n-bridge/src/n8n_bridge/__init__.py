"""n8n MCP bridge package."""

from __future__ import annotations


def main() -> None:
    """Delegate to :func:`n8n_bridge.server.main` without importing ``server`` at package import time."""
    from n8n_bridge import server as _server

    _server.main()


__all__ = ["main"]
