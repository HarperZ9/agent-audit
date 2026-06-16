from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_surface_gate_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_public_surface.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_required_public_release_files_exist() -> None:
    for name in [
        "README.md",
        "LICENSE",
        "pyproject.toml",
        ".gitignore",
        ".dockerignore",
        ".env.example",
        "project-docs/public-boundary.md",
    ]:
        assert (ROOT / name).exists(), name
