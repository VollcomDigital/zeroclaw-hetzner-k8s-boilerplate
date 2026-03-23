from pathlib import Path


def test_repository_truthfulness_contract() -> None:
    readme = Path("/workspace/README.md").read_text(encoding="utf-8")
    license_file = Path("/workspace/LICENSE")

    assert license_file.exists()
    assert "This repository currently contains **platform scaffolding and integration" in readme
    assert "mount points/placeholders rather than full" in readme
    assert "`backend/openclaw`, `backend/nemoclaw`, and `frontend/openwork`" in readme
