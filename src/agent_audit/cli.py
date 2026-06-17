"""Command line interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .auditor import AgentAuditor
from .io import (
    load_actions,
    load_intents,
    load_policies,
    write_json_report,
    write_markdown_report,
)
from .models import ActionStatus, AgentAction, IntentDeclaration, ScopePolicy


def _build_auditor(intents_path: Path, policy_path: Path | None) -> AgentAuditor:
    auditor = AgentAuditor()
    for intent in load_intents(intents_path):
        auditor.declare_intent(intent)
    if policy_path is not None:
        for policy in load_policies(policy_path):
            auditor.attach_policy(policy)
    return auditor


def _cmd_audit(args: argparse.Namespace) -> int:
    auditor = _build_auditor(args.intents, args.policy)
    report = auditor.audit_actions(load_actions(args.actions))
    write_json_report(report, args.json_out)
    if args.md_out is not None:
        write_markdown_report(report, args.md_out)
    print(
        json.dumps(
            {
                "actions": report.action_count,
                "critical": report.critical_count,
                "warnings": report.warning_count,
            },
            sort_keys=True,
        )
    )
    if args.fail_on_critical and report.critical_count:
        return 1
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    intent = IntentDeclaration.create(
        agent_id="agent-a",
        session_id="demo-session",
        objective="inspect repository release evidence",
        intended_action_kinds=("read_file", "run_test"),
        intended_target_classes=("repository", "test_suite"),
    )
    actions = [
        AgentAction.create(
            agent_id="agent-a",
            session_id="demo-session",
            action_kind="read_file",
            target_class="repository",
            target="README.md",
            reasoning="Inspect repository release evidence.",
            status=ActionStatus.EXECUTED,
        ),
        AgentAction.create(
            agent_id="agent-a",
            session_id="demo-session",
            action_kind="run_test",
            target_class="test_suite",
            target="tests/test_auditor.py",
            reasoning="Run the release evidence tests.",
            status=ActionStatus.EXECUTED,
        ),
    ]
    auditor = AgentAuditor()
    auditor.declare_intent(intent)
    auditor.attach_policy(
        ScopePolicy(
            agent_id="agent-a",
            session_id="demo-session",
            allowed_action_kinds=frozenset({"read_file", "run_test"}),
            allowed_target_classes=frozenset({"repository", "test_suite"}),
        )
    )
    report = auditor.audit_actions(actions)
    write_json_report(report, out_dir / "agent-audit-report.json")
    write_markdown_report(report, out_dir / "agent-audit-report.md")
    print(f"wrote {out_dir / 'agent-audit-report.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-audit",
        description="Audit AI-agent intent, action ledgers, and scope policy.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    audit = sub.add_parser("audit", help="audit action JSONL against intent and policy")
    audit.add_argument("--intents", required=True, type=Path)
    audit.add_argument("--actions", required=True, type=Path)
    audit.add_argument("--policy", type=Path)
    audit.add_argument("--json-out", required=True, type=Path)
    audit.add_argument("--md-out", type=Path)
    audit.add_argument("--fail-on-critical", action="store_true")
    audit.set_defaults(func=_cmd_audit)

    demo = sub.add_parser("demo", help="write a synthetic demo report")
    demo.add_argument("--out-dir", required=True, type=Path)
    demo.set_defaults(func=_cmd_demo)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
