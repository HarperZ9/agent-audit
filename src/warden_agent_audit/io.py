"""JSONL loading and report rendering."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AgentAction, AuditReport, IntentDeclaration, ScopePolicy


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_intents(path: Path) -> list[IntentDeclaration]:
    return [IntentDeclaration.from_dict(row) for row in read_jsonl(path)]


def load_actions(path: Path) -> list[AgentAction]:
    return [AgentAction.from_dict(row) for row in read_jsonl(path)]


def load_policies(path: Path) -> list[ScopePolicy]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else [data]
    return [ScopePolicy.from_dict(row) for row in rows]


def write_json_report(report: AuditReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_markdown(report: AuditReport) -> str:
    lines = [
        "# WARDEN Agent Audit",
        "",
        f"- Actions audited: {report.action_count}",
        f"- Critical findings: {report.critical_count}",
        f"- Warning findings: {report.warning_count}",
        "",
    ]
    if not report.findings:
        lines.append("No findings were emitted.")
    else:
        lines.append("## Findings")
        lines.append("")
        for finding in report.findings:
            lines.append(f"- `{finding.severity.value}` `{finding.detector_id}`: {finding.summary}")
    return "\n".join(lines) + "\n"


def write_markdown_report(report: AuditReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")
