"""Best-effort demo — not runtime-verified by author.

End-to-end walk-through of the public Agent Audit API.

It builds one intent, attaches a scope policy, audits a small action ledger
that contains a clean action and three problem actions, prints the report
summary, and writes JSON + Markdown reports to an output directory.

Run from the repository root (after `python -m pip install -e .`):

    python examples/audit_session.py

or, without installing, point Python at the source tree:

    # PowerShell
    $env:PYTHONPATH = "src"; python examples/audit_session.py
"""
from __future__ import annotations

from pathlib import Path

from agent_audit import (
    ActionStatus,
    AgentAction,
    AgentAuditor,
    IntentDeclaration,
    ScopePolicy,
)
from agent_audit.io import write_json_report, write_markdown_report


def build_report():
    auditor = AgentAuditor()

    # 1. Declare what the agent is supposed to do this session.
    auditor.declare_intent(
        IntentDeclaration.create(
            agent_id="agent-a",
            session_id="demo-session",
            objective="inspect repository release evidence",
            intended_action_kinds=["read_file", "run_test"],
            intended_target_classes=["repository", "test_suite"],
        )
    )

    # 2. Attach the scope policy that governs the session.
    auditor.attach_policy(
        ScopePolicy(
            agent_id="agent-a",
            session_id="demo-session",
            allowed_action_kinds=frozenset({"read_file", "run_test"}),
            allowed_target_classes=frozenset({"repository", "test_suite"}),
            denied_targets=frozenset({"private-notes.md"}),
            max_actions=10,
        )
    )

    # 3. Audit the action ledger. Order matters: claimed_history only fires
    #    when the prior-work claim has nothing EARLIER in the ledger to back
    #    it, so that action is placed first (prior_action_count == 0).
    actions = [
        # claimed_history: asserts prior work as the very first action, so the
        # ledger holds nothing earlier to support it.
        AgentAction.create(
            agent_id="agent-a",
            session_id="demo-session",
            action_kind="run_test",
            target_class="test_suite",
            target="tests/test_release.py",
            reasoning="I have completed the full release review already.",
            status=ActionStatus.EXECUTED,
        ),
        # Clean: declared, allowed, no prior-work claim.
        AgentAction.create(
            agent_id="agent-a",
            session_id="demo-session",
            action_kind="read_file",
            target_class="repository",
            target="README.md",
            reasoning="Inspect repository release evidence.",
            status=ActionStatus.EXECUTED,
        ),
        # intent_drift + scope_policy: kind/class never declared and not
        # allowed, and the target is explicitly denied.
        AgentAction.create(
            agent_id="agent-a",
            session_id="demo-session",
            action_kind="publish_package",
            target_class="package_registry",
            target="private-notes.md",
            reasoning="Publish the build artifact.",
            status=ActionStatus.PROPOSED,
        ),
    ]
    return auditor.audit_actions(actions)


def main() -> int:
    report = build_report()

    print(f"actions audited : {report.action_count}")
    print(f"critical        : {report.critical_count}")
    print(f"warnings        : {report.warning_count}")
    print("findings:")
    for finding in report.findings:
        print(f"  [{finding.severity.value}] {finding.detector_id}: {finding.summary}")

    out_dir = Path(__file__).resolve().parent / "out"
    json_path = out_dir / "audit_session.report.json"
    md_path = out_dir / "audit_session.report.md"
    write_json_report(report, json_path)
    write_markdown_report(report, md_path)
    print(f"\nwrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
