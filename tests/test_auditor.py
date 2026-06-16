from __future__ import annotations

from warden_agent_audit import (
    ActionStatus,
    AgentAction,
    AgentAuditor,
    AlertSeverity,
    IntentDeclaration,
    ScopePolicy,
)


def _intent() -> IntentDeclaration:
    return IntentDeclaration.create(
        agent_id="agent-a",
        session_id="session-1",
        objective="inspect repository release evidence",
        intended_action_kinds=("read_file", "run_test"),
        intended_target_classes=("repository", "test_suite"),
    )


def _action(**overrides: object) -> AgentAction:
    fields: dict[str, object] = {
        "agent_id": "agent-a",
        "session_id": "session-1",
        "action_kind": "read_file",
        "target_class": "repository",
        "target": "README.md",
        "reasoning": "Inspect repository release evidence before handoff.",
        "status": ActionStatus.EXECUTED,
    }
    fields.update(overrides)
    return AgentAction.create(**fields)


def test_clean_session_has_no_findings() -> None:
    auditor = AgentAuditor()
    auditor.declare_intent(_intent())
    auditor.attach_policy(
        ScopePolicy(
            agent_id="agent-a",
            session_id="session-1",
            allowed_action_kinds=frozenset({"read_file", "run_test"}),
            allowed_target_classes=frozenset({"repository", "test_suite"}),
            max_actions=3,
        )
    )

    report = auditor.audit_actions(
        [
            _action(),
            _action(
                action_kind="run_test",
                target_class="test_suite",
                target="tests/test_release.py",
                reasoning="Run the repository release evidence tests.",
            ),
        ]
    )

    assert report.action_count == 2
    assert report.critical_count == 0
    assert report.warning_count == 0
    assert report.findings == ()


def test_flags_drift_scope_and_hallucinated_history() -> None:
    auditor = AgentAuditor()
    auditor.declare_intent(_intent())
    auditor.attach_policy(
        ScopePolicy(
            agent_id="agent-a",
            session_id="session-1",
            allowed_action_kinds=frozenset({"read_file"}),
            allowed_target_classes=frozenset({"repository"}),
            denied_targets=frozenset({"private-notes.md"}),
        )
    )

    report = auditor.audit_actions(
        [
            _action(
                action_kind="publish_package",
                target_class="package_registry",
                target="private-notes.md",
                reasoning="I previously verified every release artifact.",
            )
        ]
    )

    assert report.critical_count == 3
    assert {finding.detector_id for finding in report.findings} == {
        "intent_drift",
        "scope_policy",
        "claimed_history",
    }
    assert all(finding.severity == AlertSeverity.CRITICAL for finding in report.findings)


def test_report_serializes_to_stable_json_shape() -> None:
    auditor = AgentAuditor()
    auditor.declare_intent(_intent())

    report = auditor.audit_actions([_action()])
    payload = report.to_dict()

    assert payload["schema"] == "warden-agent-audit.report.v1"
    assert payload["action_count"] == 1
    assert payload["critical_count"] == 0
    assert payload["findings"] == []
