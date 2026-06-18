---
type: index
tags: [index, decisions, log]
status: living-document
---

# Operational Decisions — Index

Lighter-weight decisions that don't warrant a full ADR. The continuous log format (one file, newest at top) is preserved for fast browsing and chronological context. Major architectural decisions live in [`../architecture/`](../architecture/INDEX.md) as numbered ADRs.

## Documents

| Doc | Type | Purpose |
|---|---|---|
| [decision-log.md](decision-log.md) | decision | Continuous log of UACP operational decisions, scope adjustments, deployment-specific choices. Major architectural decisions have been promoted to ADRs (see related). |

## When to log here vs author an ADR

| Use the decision-log when | Use an ADR when |
|---|---|
| Operational choice with limited scope | Architectural decision with cross-cutting consequences |
| Scope adjustment, naming convention | New enforcement surface or invariant |
| Tactical deployment choice | Long-lived contract change |
| Decision is unlikely to be revisited | Decision may be superseded; needs traceable lifecycle |
