"""Regression: Makefile awk extracts env values when = is surrounded by optional spaces."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(not shutil.which("bash"), reason="Makefile uses bash; awk extraction tests require bash")


def _awk_env_second_field(key: str, env_path: Path) -> str:
    """Mirror Makefile: awk -F ' *= *' '/^KEY[[:space:]]*=/ {print $2; exit}' file."""
    script = (
        rf"awk -F ' *= *' '/^{key}[[:space:]]*=/ {{print $2; exit}}' {env_path}"
    )
    result = subprocess.run(
        ["bash", "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("OLLAMA_MODEL=qwen\n", "qwen"),
        ("OLLAMA_MODEL = qwen\n", "qwen"),
        ("OLLAMA_MODEL= qwen\n", "qwen"),
        ("OLLAMA_MODEL  =  qwen\n", "qwen"),
    ],
)
def test_awk_extracts_ollama_model_with_spacing_variants(line: str, expected: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as handle:
        handle.write(line)
        path = Path(handle.name)
    try:
        assert _awk_env_second_field("OLLAMA_MODEL", path) == expected
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("VLLM_MODEL=meta-llama/Llama-3\n", "meta-llama/Llama-3"),
        ("VLLM_MODEL = meta-llama/Llama-3\n", "meta-llama/Llama-3"),
    ],
)
def test_awk_extracts_vllm_model_with_spacing_variants(line: str, expected: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as handle:
        handle.write(line)
        path = Path(handle.name)
    try:
        assert _awk_env_second_field("VLLM_MODEL", path) == expected
    finally:
        path.unlink(missing_ok=True)
