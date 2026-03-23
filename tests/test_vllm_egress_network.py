"""Prod vLLM must reach Hugging Face on first boot; internal-only ai-tier blocks egress."""

from pathlib import Path


def test_prod_vllm_uses_egress_tier_for_huggingface_while_staying_on_ai_mesh() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    prod = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert "  egress-tier:\n    name: hybrid_egress_tier\n    internal: false" in prod

    vllm_start = prod.index("  vllm:")
    vllm_end = prod.index("  1password-connect-api:", vllm_start)
    vllm_block = prod[vllm_start:vllm_end]
    assert "- egress-tier" in vllm_block
    assert "- ai-tier" in vllm_block
    assert vllm_block.index("- egress-tier") < vllm_block.index("- ai-tier")
