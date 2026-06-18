# Usage

Agent Audit compares a declared agent **intent** plus an **action ledger**
against a **scope policy**, and emits findings for three classes of problem:

- `intent_drift` — an action diverges from the declared intent for its
  `(agent_id, session_id)`.
- `scope_policy` — an action violates an attached scope policy (denied or
  not-allowed action kind / target class, a denied target, or the session
  action limit).
- `claimed_history` — an action's `reasoning` asserts prior work (e.g.
  "I previously…", "I have completed…") that is not backed by earlier
  actions in the ledger.

There are no runtime dependencies; Python 3.10+ is required.

## Install

```powershell
python -m pip install -e .[dev]
```

This installs the `agent-audit` console script and the importable
`agent_audit` package.

## CLI

The CLI exposes two subcommands: `audit` and `demo`.

```
agent-audit --version
agent-audit audit  --intents PATH --actions PATH --json-out PATH
                   [--policy PATH] [--md-out PATH] [--fail-on-critical]
agent-audit demo   --out-dir PATH
```

`audit` flags (exactly these — no others exist):

| Flag                | Required | Type | Meaning                                              |
| ------------------- | -------- | ---- | ---------------------------------------------------- |
| `--intents`         | yes      | path | JSONL file of intent declarations (one per line)     |
| `--actions`         | yes      | path | JSONL file of agent actions (one per line)           |
| `--json-out`        | yes      | path | where to write the JSON report                       |
| `--policy`          | no       | path | JSON file: a single policy object or a list of them  |
| `--md-out`          | no       | path | where to write the Markdown report                   |
| `--fail-on-critical`| no       | flag | exit `1` if any critical finding is emitted          |

Intents and actions are matched to policies by the `(agent_id, session_id)`
pair. An action with no matching intent is itself a critical `intent_drift`
finding.

The `audit` command also prints a one-line JSON summary to stdout, e.g.
`{"actions": 2, "critical": 0, "warnings": 0}`.

### Example 1 — audit the bundled synthetic fixtures (clean session)

```powershell
agent-audit audit `
  --intents fixtures/agent_session/intents.jsonl `
  --actions fixtures/agent_session/actions.jsonl `
  --policy  fixtures/agent_session/policy.json `
  --json-out out/report.json `
  --md-out   out/report.md
```

Stdout:

```json
{"actions": 2, "critical": 0, "warnings": 0}
```

`out/report.json`:

```json
{
  "action_count": 2,
  "critical_count": 0,
  "findings": [],
  "schema": "agent-audit.report.v1",
  "warning_count": 0
}
```

`out/report.md`:

```markdown
# Agent Audit

- Actions audited: 2
- Critical findings: 0
- Warning findings: 0

No findings were emitted.
```

### Example 2 — a session with scope and drift violations

`intents.jsonl` (one JSON object per line):

```json
{"agent_id":"agent-a","session_id":"session-1","objective":"inspect repository release evidence","intended_action_kinds":["read_file","run_test"],"intended_target_classes":["repository","test_suite"]}
```

`actions.jsonl`:

```json
{"agent_id":"agent-a","session_id":"session-1","action_kind":"read_file","target_class":"repository","target":"README.md","reasoning":"Inspect repository release evidence.","status":"executed"}
{"agent_id":"agent-a","session_id":"session-1","action_kind":"publish_package","target_class":"package_registry","target":"private-notes.md","reasoning":"I previously verified every release artifact.","status":"executed"}
```

`policy.json`:

```json
{"agent_id":"agent-a","session_id":"session-1","allowed_action_kinds":["read_file","run_test"],"allowed_target_classes":["repository","test_suite"],"denied_targets":["private-notes.md"]}
```

Run:

```powershell
agent-audit audit `
  --intents intents.jsonl --actions actions.jsonl --policy policy.json `
  --json-out report.json --md-out report.md --fail-on-critical
```

Stdout (and the process exits `1` because of `--fail-on-critical`):

```json
{"actions": 2, "critical": 2, "warnings": 0}
```

The second action trips two detectors — it both diverges from the declared
intent (`publish_package`/`package_registry` was never declared) and breaks
the scope policy (kind and class not allowed, target denied). The Markdown
report:

```markdown
# Agent Audit

- Actions audited: 2
- Critical findings: 2
- Warning findings: 0

## Findings

- `critical` `intent_drift`: action diverges from declared intent
- `critical` `scope_policy`: action_kind 'publish_package' is not allowed; target_class 'package_registry' is not allowed; target 'private-notes.md' is denied
```

> Note: the `claimed_history` detector does **not** fire here. It only fires
> when a prior-work claim has nothing earlier in the ledger to back it; in
> this session the offending action already has a prior action recorded. See
> Example 3 for a claim that is flagged.

### Example 3 — write a synthetic demo report

```powershell
agent-audit demo --out-dir out
```

This writes `out/agent-audit-report.json` and `out/agent-audit-report.md`
for a clean two-action session (no findings) and prints the path of the JSON
report.

## Python API

The package exports its public surface from the top-level `agent_audit`
module:

```python
from agent_audit import (
    AgentAuditor,        # the auditor
    IntentDeclaration,   # declared intent (use IntentDeclaration.create(...))
    AgentAction,         # one ledger entry (use AgentAction.create(...))
    ScopePolicy,         # scope rules
    ActionStatus,        # proposed | executed | failed | denied
    AlertSeverity,       # info | warn | critical
    AuditFinding,        # one finding
    AuditReport,         # result of audit_actions(...)
)
```

### Example 4 — audit a session in code

```python
from agent_audit import (
    AgentAuditor, IntentDeclaration, AgentAction, ScopePolicy, ActionStatus,
)

auditor = AgentAuditor()

auditor.declare_intent(
    IntentDeclaration.create(
        agent_id="agent-a",
        session_id="s1",
        objective="inspect repository release evidence",
        intended_action_kinds=["read_file", "run_test"],
        intended_target_classes=["repository", "test_suite"],
    )
)

auditor.attach_policy(
    ScopePolicy(
        agent_id="agent-a",
        session_id="s1",
        allowed_action_kinds=frozenset({"read_file", "run_test"}),
        allowed_target_classes=frozenset({"repository", "test_suite"}),
        max_actions=10,
    )
)

report = auditor.audit_actions([
    AgentAction.create(
        agent_id="agent-a",
        session_id="s1",
        action_kind="delete_file",      # never declared, not allowed
        target_class="repository",      # declared/allowed
        target="LICENSE",
        reasoning="Remove the license file.",
        status=ActionStatus.PROPOSED,
    ),
])

print(report.action_count)     # 1
print(report.critical_count)   # 1
print(report.warning_count)    # 1
for finding in report.findings:
    print(finding.detector_id, finding.severity.value, "-", finding.summary)
```

Output:

```
1
1
1
intent_drift warn - action diverges from declared intent
scope_policy critical - action_kind 'delete_file' is not allowed
```

Here the action's `target_class` matches the intent but its `action_kind`
does not, so `intent_drift` is only a warning; the scope policy disallows the
kind outright, so `scope_policy` is critical.

Call `report.to_dict()` for the JSON-serializable report shape (the same
structure written by `--json-out`), or use the helpers in `agent_audit.io`
(`write_json_report`, `write_markdown_report`, `render_markdown`,
`load_intents`, `load_actions`, `load_policies`) to read JSONL/JSON inputs and
render reports.

---

All examples above were run against version 0.1.1; outputs are reproduced from
actual runs except where `action_id` values (which are random UUID-derived)
have been omitted for brevity.
