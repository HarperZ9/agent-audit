"""Agent behavior auditor."""
from __future__ import annotations

from collections import defaultdict

from .models import (
    AgentAction,
    AlertSeverity,
    AuditFinding,
    AuditReport,
    IntentDeclaration,
    ScopePolicy,
    _norm_words,
)


_CLAIMED_HISTORY_MARKERS = (
    "i previously",
    "i already",
    "i have completed",
    "after completing",
    "given my earlier",
    "having run",
)


class AgentAuditor:
    """Audit declared agent intent against an action ledger."""

    def __init__(self) -> None:
        self._intents: dict[tuple[str, str], IntentDeclaration] = {}
        self._policies: dict[tuple[str, str], ScopePolicy] = {}

    def declare_intent(self, intent: IntentDeclaration) -> None:
        self._intents[(intent.agent_id, intent.session_id)] = intent

    def attach_policy(self, policy: ScopePolicy) -> None:
        self._policies[(policy.agent_id, policy.session_id)] = policy

    def audit_actions(self, actions: list[AgentAction]) -> AuditReport:
        findings: list[AuditFinding] = []
        prior_by_session: dict[tuple[str, str], list[AgentAction]] = defaultdict(list)
        for action in actions:
            key = (action.agent_id, action.session_id)
            intent = self._intents.get(key)
            policy = self._policies.get(key)
            findings.extend(self._check_intent(action, intent))
            if policy is not None:
                findings.extend(
                    self._check_scope(action, policy, len(prior_by_session[key]))
                )
            findings.extend(self._check_claimed_history(action, prior_by_session[key]))
            prior_by_session[key].append(action)
        return AuditReport(action_count=len(actions), findings=tuple(findings))

    def _check_intent(
        self, action: AgentAction, intent: IntentDeclaration | None
    ) -> list[AuditFinding]:
        if intent is None:
            return [
                AuditFinding(
                    detector_id="intent_drift",
                    severity=AlertSeverity.CRITICAL,
                    action_id=action.action_id,
                    summary="action has no declared intent for this agent session",
                    detail={"agent_id": action.agent_id, "session_id": action.session_id},
                )
            ]
        kind_match = action.action_kind in intent.intended_action_kinds
        class_match = action.target_class in intent.intended_target_classes
        words = set(_norm_words(f"{action.target} {action.reasoning}"))
        keyword_overlap = bool(words & set(intent.objective_keywords))
        if kind_match and class_match:
            return []
        severity = (
            AlertSeverity.CRITICAL
            if not kind_match and not class_match
            else AlertSeverity.WARN
        )
        return [
            AuditFinding(
                detector_id="intent_drift",
                severity=severity,
                action_id=action.action_id,
                summary="action diverges from declared intent",
                detail={
                    "kind_match": kind_match,
                    "class_match": class_match,
                    "keyword_overlap": keyword_overlap,
                },
            )
        ]

    def _check_scope(
        self, action: AgentAction, policy: ScopePolicy, prior_count: int
    ) -> list[AuditFinding]:
        reasons = []
        if action.action_kind in policy.denied_action_kinds:
            reasons.append(f"action_kind {action.action_kind!r} is denied")
        if policy.allowed_action_kinds and action.action_kind not in policy.allowed_action_kinds:
            reasons.append(f"action_kind {action.action_kind!r} is not allowed")
        if action.target_class in policy.denied_target_classes:
            reasons.append(f"target_class {action.target_class!r} is denied")
        if policy.allowed_target_classes and action.target_class not in policy.allowed_target_classes:
            reasons.append(f"target_class {action.target_class!r} is not allowed")
        if action.target in policy.denied_targets:
            reasons.append(f"target {action.target!r} is denied")
        if policy.max_actions is not None and prior_count >= policy.max_actions:
            reasons.append(f"session action limit reached at {prior_count}")
        if not reasons:
            return []
        return [
            AuditFinding(
                detector_id="scope_policy",
                severity=AlertSeverity.CRITICAL,
                action_id=action.action_id,
                summary="; ".join(reasons),
                detail={"prior_action_count": prior_count},
            )
        ]

    def _check_claimed_history(
        self, action: AgentAction, prior_actions: list[AgentAction]
    ) -> list[AuditFinding]:
        reasoning = action.reasoning.lower()
        marker = next((m for m in _CLAIMED_HISTORY_MARKERS if m in reasoning), "")
        if not marker:
            return []
        prior_ids = {a.action_id for a in prior_actions}
        missing_refs = [ref for ref in action.evidence_refs if ref not in prior_ids]
        if prior_actions and not missing_refs:
            return []
        detail = {"marker": marker, "prior_action_count": len(prior_actions)}
        if missing_refs:
            detail["missing_evidence_refs"] = missing_refs
        return [
            AuditFinding(
                detector_id="claimed_history",
                severity=AlertSeverity.CRITICAL,
                action_id=action.action_id,
                summary="reasoning claims prior work that is not present in the ledger",
                detail=detail,
            )
        ]
