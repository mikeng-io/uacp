# Operator Summary + Package Sufficiency Lessons — 2026-05-19

## Context

During a UACP/Nora identity-registry run, the operator observed two failures:

1. Telegram/Discord phase returns exposed raw audit substrate: edited-file lists, created-path inventories, commit/file stats, and validation detail. The operator wanted information, not raw data.
2. A light/standard UACP task produced only YAML lifecycle envelopes and treated Markdown package docs as optional. The operator rejected that because the task crossed a public/private identity boundary and needed enough human-readable “why” and “how” to support review.

## Durable lessons

### 1. Operator phase returns are summaries, not evidence dumps

Default chat returns should be decision-grade:

- conclusion/status
- what changed at meaning level
- why it matters / rational intent
- decision and rationale
- invariants preserved
- material risks
- next action
- compact evidence pointer

Do not paste full file lists, raw diff stats, raw validation logs, complete artifact inventories, or council transcripts unless the operator asks for audit detail or a blocker/rollback depends on a specific path.

### 2. “Light” does not mean “YAML-only”

YAML artifacts are machine lifecycle envelopes. They are not automatically sufficient as the human review surface.

For any task involving privacy boundaries, public/private profile behavior, runtime prompt context injection, identity data, Guardian/Heartgate/validator behavior, governance policy, irreversible side effects, or complex rollback/verification requirements, create a minimal human-readable package even when the task is otherwise small.

Minimum package content should preserve:

- what is changing
- why it is changing
- scope and containment
- authority and side effects
- invariants
- risks and verification
- rollback/recovery
- transition readiness

### 3. Adaptive package rule

Package size is adaptive. A small task may need only 3–5 concise Markdown files. A serious governance/runtime task may need a fuller modular package. The mistake to avoid is treating docs as optional merely because the run is not full-governance.

## Practical check

Before leaving PROPOSE or PLAN, ask:

> If a future reviewer only saw the YAML envelopes, would they understand the why/how/invariants well enough to safely execute or verify this task?

If no, write the package docs and package-selection bridge before advancing.
