"""Core public data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm_words(text: str) -> tuple[str, ...]:
    words = []
    for raw in text.split():
        word = raw.strip().strip(".,;:!?\"'()[]{}").lower()
        if len(word) > 2:
            words.append(word)
    return tuple(words)


class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    EXECUTED = "executed"
    FAILED = "failed"
    DENIED = "denied"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


@dataclass(frozen=True)
class IntentDeclaration:
    agent_id: str
    session_id: str
    objective: str
    intended_action_kinds: tuple[str, ...]
    intended_target_classes: tuple[str, ...]
    objective_keywords: tuple[str, ...]
    intent_id: str = field(default_factory=lambda: f"INT-{uuid.uuid4().hex[:16]}")
    declared_utc: str = field(default_factory=_utc_now)

    @classmethod
    def create(
        cls,
        *,
        agent_id: str,
        session_id: str,
        objective: str,
        intended_action_kinds: tuple[str, ...] | list[str],
        intended_target_classes: tuple[str, ...] | list[str],
        objective_keywords: tuple[str, ...] | list[str] = (),
    ) -> "IntentDeclaration":
        if not agent_id or not session_id or not objective:
            raise ValueError("agent_id, session_id, and objective are required")
        if not intended_action_kinds or not intended_target_classes:
            raise ValueError("intent must include action kinds and target classes")
        keywords = tuple(objective_keywords) or _norm_words(objective)
        return cls(
            agent_id=agent_id,
            session_id=session_id,
            objective=objective,
            intended_action_kinds=tuple(intended_action_kinds),
            intended_target_classes=tuple(intended_target_classes),
            objective_keywords=tuple(_norm_words(" ".join(keywords))),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntentDeclaration":
        intent = cls.create(
            agent_id=str(data["agent_id"]),
            session_id=str(data["session_id"]),
            objective=str(data["objective"]),
            intended_action_kinds=tuple(data["intended_action_kinds"]),
            intended_target_classes=tuple(data["intended_target_classes"]),
            objective_keywords=tuple(data.get("objective_keywords", ())),
        )
        return cls(
            **{
                **intent.__dict__,
                "intent_id": str(data.get("intent_id", intent.intent_id)),
                "declared_utc": str(data.get("declared_utc", intent.declared_utc)),
            }
        )


@dataclass(frozen=True)
class AgentAction:
    action_id: str
    agent_id: str
    session_id: str
    action_kind: str
    target_class: str
    target: str
    reasoning: str
    status: ActionStatus
    evidence_refs: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
    recorded_utc: str = field(default_factory=_utc_now)

    @classmethod
    def create(
        cls,
        *,
        agent_id: str,
        session_id: str,
        action_kind: str,
        target_class: str,
        target: str,
        reasoning: str,
        status: ActionStatus | str = ActionStatus.PROPOSED,
        evidence_refs: tuple[str, ...] | list[str] = (),
        parameters: dict[str, Any] | None = None,
        action_id: str | None = None,
        recorded_utc: str | None = None,
    ) -> "AgentAction":
        if not agent_id or not session_id or not action_kind or not target_class:
            raise ValueError("agent_id, session_id, action_kind, target_class required")
        if not target or not reasoning:
            raise ValueError("target and reasoning are required")
        action_status = status if isinstance(status, ActionStatus) else ActionStatus(str(status))
        return cls(
            action_id=action_id or f"ACT-{uuid.uuid4().hex[:16]}",
            agent_id=agent_id,
            session_id=session_id,
            action_kind=action_kind,
            target_class=target_class,
            target=target,
            reasoning=reasoning,
            status=action_status,
            evidence_refs=tuple(evidence_refs),
            parameters=dict(parameters or {}),
            recorded_utc=recorded_utc or _utc_now(),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentAction":
        return cls.create(
            agent_id=str(data["agent_id"]),
            session_id=str(data["session_id"]),
            action_kind=str(data["action_kind"]),
            target_class=str(data["target_class"]),
            target=str(data["target"]),
            reasoning=str(data["reasoning"]),
            status=data.get("status", ActionStatus.PROPOSED),
            evidence_refs=tuple(data.get("evidence_refs", ())),
            parameters=dict(data.get("parameters", {})),
            action_id=data.get("action_id"),
            recorded_utc=data.get("recorded_utc"),
        )


@dataclass(frozen=True)
class ScopePolicy:
    agent_id: str
    session_id: str
    allowed_action_kinds: frozenset[str] = frozenset()
    denied_action_kinds: frozenset[str] = frozenset()
    allowed_target_classes: frozenset[str] = frozenset()
    denied_target_classes: frozenset[str] = frozenset()
    denied_targets: frozenset[str] = frozenset()
    max_actions: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScopePolicy":
        return cls(
            agent_id=str(data["agent_id"]),
            session_id=str(data["session_id"]),
            allowed_action_kinds=frozenset(data.get("allowed_action_kinds", ())),
            denied_action_kinds=frozenset(data.get("denied_action_kinds", ())),
            allowed_target_classes=frozenset(data.get("allowed_target_classes", ())),
            denied_target_classes=frozenset(data.get("denied_target_classes", ())),
            denied_targets=frozenset(data.get("denied_targets", ())),
            max_actions=data.get("max_actions"),
        )


@dataclass(frozen=True)
class AuditFinding:
    detector_id: str
    severity: AlertSeverity
    action_id: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detector_id": self.detector_id,
            "severity": self.severity.value,
            "action_id": self.action_id,
            "summary": self.summary,
            "detail": dict(self.detail),
        }


@dataclass(frozen=True)
class AuditReport:
    action_count: int
    findings: tuple[AuditFinding, ...]
    schema: str = "agent-audit.report.v1"

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AlertSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AlertSeverity.WARN)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "action_count": self.action_count,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "findings": [finding.to_dict() for finding in self.findings],
        }
