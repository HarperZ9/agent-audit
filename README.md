# Agent Audit

> Audit an AI-agent session — declared intent + action ledger vs. a scope policy; flags drift, scope violations, and unbacked prior-work claims.

[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![version](https://img.shields.io/badge/version-0.1.1-informational.svg)
[![CI](https://github.com/HarperZ9/agent-audit/actions/workflows/tests.yml/badge.svg)](https://github.com/HarperZ9/agent-audit/actions/workflows/tests.yml)
![deps: none](https://img.shields.io/badge/deps-none-success.svg)
[![part of: AI-accountability toolkit](https://img.shields.io/badge/part_of-AI--accountability_toolkit-7a5cff.svg)](https://harperz9.github.io)

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
agent-audit demo --out-dir out
agent-audit audit --intents fixtures/agent_session/intents.jsonl --actions fixtures/agent_session/actions.jsonl --policy fixtures/agent_session/policy.json --json-out out/report.json --md-out out/report.md
```

## Usage

See [USAGE.md](USAGE.md) for the full CLI and Python-API reference, worked
examples with expected output, and a runnable script under
[`examples/`](examples/).

## Boundary

Examples are synthetic. The package ships only synthetic repository-review actions and does not include any private operational data.

---
**Zain Dana Harper** — small tools with explicit edges.
[Portfolio](https://harperz9.github.io) · [HarperZ9](https://github.com/HarperZ9)
<sub>Built with Claude Code; reviewed, tested, and owned by me.</sub>
