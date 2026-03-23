"""Ensure ``import n8n_bridge`` does not execute ``server`` module initialization."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_import_n8n_bridge_package_does_not_load_server_module() -> None:
    """Side-effect-heavy server (logger, MCP, caches) must not run on ``import n8n_bridge``."""
    src_root = Path(__file__).resolve().parents[1] / "src"
    code = (
        "import n8n_bridge\n"
        "import sys\n"
        "assert 'n8n_bridge.server' not in sys.modules\n"
    )
    env = {**os.environ, "PYTHONPATH": str(src_root)}
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
