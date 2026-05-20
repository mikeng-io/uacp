---
type: guide-index
tags: [uacp, lifecycle, semantic-packages, heartgate, guardian, documentation]
status: living-document
owner: UACP documentation
canonical_authority: false
---

# Lifecycle Hardening Guide — Reading Order

This guide explains the UACP lifecycle-hardening series in human-readable and agent-operable form. It exists because the changes span semantic packages, operator presentation, Phase Intent Verification, VERIFY/RESOLVE gates, Heartgate runtime enforcement, Guardian path binding, validator parity, active skills, and audit remediation.

The guide is intentionally modular. One large document would hide the phase boundaries; scattered edits would fracture the doctrine. Use this directory as the conductor for the topic.

## Read order

1. [01-human-overview.md](01-human-overview.md) — why the hardening exists and how to explain it to a human.
2. [02-agent-operating-guide.md](02-agent-operating-guide.md) — what future agents must do when touching this area.
3. [03-artifact-and-gate-map.md](03-artifact-and-gate-map.md) — where each phase records meaning, evidence, and runtime checks.
4. [04-audit-and-remediation-history.md](04-audit-and-remediation-history.md) — what Kimi/Codex/full-lineage audits found and how the remediation closed the loop.

## Canonical sources

This guide summarizes and routes. Authority remains with:

- `config/phase-transitions.yaml` — phase gates and transition contracts.
- `config/state.yaml` and `state/current.yaml` — governed state pointer contracts and current state.
- `scripts/validate_uacp_artifacts.py` — offline artifact and linked-transition validation.
- `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` — Guardian and Heartgate runtime enforcement.
- `docs/reference/lifecycle-trace-table.md` — transition-by-transition evidence map.
- `docs/reference/operator-phase-return-schema.md` — operator-facing presentation contract.
- ADRs `0010` through `0014` under `docs/architecture/` — accepted decision history for the hardening series.

## Anti-fracture rule

When updating lifecycle hardening documentation:

- Put explanations here.
- Put phase semantics in `docs/lifecycle/`.
- Put runtime enforcement details in `docs/runtime/`.
- Put schema/field contracts in `docs/reference/` or `config/`.
- Put historical decisions in ADRs.
- Put machine enforcement in validator/runtime code.

Do not duplicate the same rule in multiple prose locations. Link to the owner instead.

## Current status

As of commit `c28da46`, the full-lineage remediation pass is committed and pushed. The repo validator, Heartgate runtime smoke, active skill-link checker, and negative fixture sweep passed before commit.
