---
type: reference
title: Operator Phase-Return Schema
description: Presentation contract for operator phase summaries — conclusion-first summaries with evidence pointers, not raw data dumps.
tags: [operator-interface, presentation, schema, lifecycle]
timestamp: 2026-06-18
---

# Operator Phase-Return Schema

## Purpose

UACP phase work produces two different surfaces:

1. **Evidence layer** — raw artifacts, changed paths, validation logs, diffs, council synthesis, gate-ledger records, and rollback evidence.
2. **Operator summary layer** — the concise meaning of the phase result for Telegram, Discord, or any human control channel.

Default phase returns MUST use the operator summary layer. Raw evidence remains preserved in artifacts, but it MUST NOT be dumped into operator chat unless it is directly needed for a decision, an error, rollback, or the operator explicitly asks for details.

## Rationale

The operator needs information, not raw data. File inventories and large path lists are audit substrate. They are useful for verification, but they obscure the conclusion in a messaging channel and burn attention.

The rational intent is to keep UACP evidence complete while making phase communication decision-grade: conclusion first, why it matters, what decision is being made, what invariants are preserved, what risks remain, and what happens next.

## Schema

```yaml
kind: uacp.operator_phase_return
version: 1
run_id: string
phase: triage | propose | plan | execute | verify | resolve
status: pass | warn | block | in_progress
conclusion: string
what_changed:
  - string
why_it_matters:
  - string
decision:
  result: string
  rationale: string
invariants_preserved:
  - string
risks:
  - severity: low | medium | high | critical
    summary: string
    handling: resolved | accepted | deferred | blocked
next_action:
  recommendation: string
  requires_operator: boolean
  reason: string
evidence_pointer:
  commit: optional string
  artifact_index: optional string
  verification_summary: optional string
raw_details_available: boolean
```

## Telegram / Discord rendering

Render the schema as compact text, not YAML, unless a machine-readable artifact is requested.

Template:

```text
{PHASE} {status}: {conclusion}

What changed:
- {one to three meaning-level bullets}

Why it matters:
- {rational intent / consequence}

Decision:
{result}. {rationale}

Invariants:
- {preserved invariant}
- {preserved invariant}

Risks:
- {severity}: {summary}; {handling}

Next:
{recommendation}

Evidence:
{commit/artifact/verification pointer}. Raw details available on request.
```

## Suppression rules

Do not include by default:

- full edited-file lists
- full newly-created-file lists
- raw `git diff --stat` output
- raw validation logs
- raw council transcripts
- complete artifact inventories
- large YAML/JSON snippets

Include specific paths only when:

- a path is the decision subject
- an error or blocker depends on that path
- rollback requires naming the target
- the operator explicitly asks for audit detail
- the message is a handoff to an implementation worker rather than an operator phase return

## Invariants

- Evidence completeness is preserved in repo artifacts and logs.
- Operator chat is summary-first and decision-grade.
- A phase return must state conclusion, rational intent, decision/status, invariants, risks, and next action.
- Raw details are available by pointer, not pasted by default.
- The schema applies to TRIAGE, PROPOSE, PLAN, EXECUTE, VERIFY, and RESOLVE returns.
- This schema governs presentation only; it does not weaken Heartgate, Guardian, validator, council, or gate-ledger evidence requirements.
