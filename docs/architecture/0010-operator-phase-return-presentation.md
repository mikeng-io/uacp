# ADR 0010: Separate Operator Phase Returns from Raw Evidence

Status: accepted
Date: 2026-05-19

## What changed

UACP now defines an operator phase-return presentation contract for Telegram, Discord, and other human control channels.

The contract is documented in `docs/reference/operator-phase-return-schema.md` and requires phase returns to summarize:

- conclusion
- what changed at meaning level
- why it matters / rational intent
- decision and rationale
- invariants preserved
- risks and handling
- next action
- compact evidence pointers

The active UACP lifecycle skills are updated to use summary-first phase returns and to avoid dumping raw file lists, raw diff stats, artifact inventories, validator logs, or council transcripts into operator chat by default.

## Why we are changing it

Previous phase returns exposed the evidence layer directly to the operator channel: long file lists, newly-created paths, raw stats, and low-level artifact inventories. That data is necessary for auditability, but it is usually not the information the operator needs to decide what happens next.

The rational intent is to preserve complete evidence while making phase communication decision-grade. Operator channels should answer: what happened, why it matters, what is decided, what remains risky, and what the next action is.

## Decision

Adopt a two-layer presentation model:

1. Evidence layer: complete raw artifacts, diffs, validation logs, council evidence, commit IDs, and gate-ledger records.
2. Operator summary layer: concise phase-return schema rendered as human text.

The operator summary layer is the default for Telegram/Discord. Raw details remain available by pointer and on request.

## Invariants

- UACP evidence completeness is not reduced.
- Heartgate, Guardian, validator, council, and gate-ledger requirements are unchanged.
- Operator chat must be conclusion-first and decision-grade.
- Raw file lists are suppressed by default unless needed for a blocker, rollback, explicit decision, or operator-requested audit detail.
- Each phase return must state conclusion, intent, decision/status, invariants, risks, next action, and evidence pointer.
- The schema governs presentation only; it must not become a loophole for skipping raw evidence capture.

## Consequences

Positive:

- Operator attention is spent on decisions and risk, not raw path inventories.
- Phase outputs become consistent across TRIAGE, PROPOSE, PLAN, EXECUTE, VERIFY, and RESOLVE.
- Detailed audit evidence remains discoverable without being pushed into chat by default.

Tradeoff:

- Agents must maintain a stronger distinction between evidence writing and operator reporting.
- A poor summary can hide important detail, so risks and blockers must be explicitly summarized and evidence pointers must remain available.

## Verification

- `docs/reference/operator-phase-return-schema.md` exists and is indexed.
- ADR index references this decision.
- Active lifecycle skill exports include operator phase-return rules.
- UACP artifact validator still passes for config/schema coherence.
