from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_cli_audit_writes_json_and_markdown(tmp_path: Path) -> None:
    intents = tmp_path / "intents.jsonl"
    actions = tmp_path / "actions.jsonl"
    policy = tmp_path / "policy.json"
    report = tmp_path / "report.json"
    markdown = tmp_path / "report.md"

    _write_jsonl(
        intents,
        [
            {
                "agent_id": "agent-a",
                "session_id": "session-1",
                "objective": "inspect repository release evidence",
                "intended_action_kinds": ["read_file"],
                "intended_target_classes": ["repository"],
            }
        ],
    )
    _write_jsonl(
        actions,
        [
            {
                "agent_id": "agent-a",
                "session_id": "session-1",
                "action_kind": "read_file",
                "target_class": "repository",
                "target": "README.md",
                "reasoning": "Inspect repository release evidence.",
                "status": "executed",
            }
        ],
    )
    policy.write_text(
        json.dumps(
            {
                "agent_id": "agent-a",
                "session_id": "session-1",
                "allowed_action_kinds": ["read_file"],
                "allowed_target_classes": ["repository"],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "warden_agent_audit",
            "audit",
            "--intents",
            str(intents),
            "--actions",
            str(actions),
            "--policy",
            str(policy),
            "--json-out",
            str(report),
            "--md-out",
            str(markdown),
            "--fail-on-critical",
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["action_count"] == 1
    assert payload["critical_count"] == 0
    assert "WARDEN Agent Audit" in markdown.read_text(encoding="utf-8")


def test_cli_demo_emits_report(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "warden_agent_audit",
            "demo",
            "--out-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "agent-audit-report.json").exists()
    assert (tmp_path / "agent-audit-report.md").exists()
