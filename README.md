# WARDEN Agent Audit

WARDEN Agent Audit is a dependency-light public package for reviewing AI-agent work. It records declared intent, action ledgers, scope policy, detector findings, and handoff reports without depending on private WARDEN infrastructure.

The package is built for local review loops:

- declare what an agent is supposed to do
- log what the agent proposed or executed
- attach a session policy
- detect intent drift, scope policy violations, and claimed prior work that is not present in the ledger
- emit JSON and Markdown reports for human review

## Install

```powershell
python -m pip install -e .[dev]
```

## Run

```powershell
warden-agent-audit demo --out-dir out
warden-agent-audit audit --intents fixtures/agent_session/intents.jsonl --actions fixtures/agent_session/actions.jsonl --policy fixtures/agent_session/policy.json --json-out out/report.json --md-out out/report.md
```

## Boundary

This is a public-safe extraction. It does not publish private operations, private corpora, session transcripts, client data, provider integrations, or private WARDEN policy material. Examples use synthetic repository-review actions only.
