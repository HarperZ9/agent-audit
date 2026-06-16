from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", "build", "dist", "out"}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".txt", ".yml", ".yaml", ".json", ".jsonl", ".example"}
REQUIRED = [
    "README.md",
    "LICENSE",
    "pyproject.toml",
    ".gitignore",
    ".dockerignore",
    ".env.example",
    "project-docs/public-boundary.md",
]
BANNED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        "warden" + r"-ops",
        "the" + r"-cloner",
        "command" + r" server",
        "jail" + r"break",
        "by" + r"pass",
        "ex" + r"ploit",
        r"AKIA[0-9A-Z]{16}",
        r"OPENAI_API_KEY\s*=",
        r"ANTHROPIC_API_KEY\s*=",
    ]
]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def main() -> int:
    failures: list[str] = []
    for required in REQUIRED:
        if not (ROOT / required).exists():
            failures.append(f"missing required file: {required}")
    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        if path.name == ".env":
            failures.append("committed .env file is not allowed")
        if path.suffix not in TEXT_SUFFIXES and path.name != ".gitignore":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in BANNED_PATTERNS:
            if pattern.search(text):
                failures.append(f"{rel}: banned public-surface pattern {pattern.pattern!r}")
    if failures:
        for failure in failures:
            print(failure)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
