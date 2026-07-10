---
type: design
title: Minimal-non-leading dispatch — plumb the existing context_policy into review/audit
description: The correctness fix. For Tier >=2 review/audit dispatch, the runtime_input carries a minimal-non-leading engagement spec (scope + diff/baseline pointer, hard constraints) and strips the leading narrative (expected findings, suspected cause, preferred design, desired verdict). Defines the retain-vs-strip contract and where it plugs into phase-3/phase-4/uacp-bridge.
tags: [context-policy, minimal-non-leading, runtime-input, dispatch, review, audit]
timestamp: 2026-07-10
edges:
  - {dst: 01-narrative-vs-spec, rel: realizes, provenance: asserted}
---

# Minimal-non-leading dispatch

## What changes

Today `context_policy` exists in the `uacp-bridge` input schema but is (a) not projected into the
Tier >=2 `runtime_input` and (b) only exercised for brainstorm Round 1. This node makes
`minimal-non-leading` the **default context policy for external-runtime `review` / `audit`
dispatch**, and defines what that policy retains vs strips so the reviewer gets the engagement
specification without the leading narrative ([[01-narrative-vs-spec]]).

This is the **correctness / hygiene** half of the bundle: it is what lets us remove the orchestrator's
opinion *without* starving the reviewer of the artifact. It must land before or together with any
change that reduces what is pushed. Frame it honestly (per the cross-provider council, [[00-problem]]):
this is *minimal-non-leading dispatch hygiene + the two break fixes*, **not** a claim that the reviewer
became independent — that is the deferred [[11-grounding-provenance]].

**Where the pieces already live (precision from the council):** the *discipline* — the exact Round-1
"exclude expected findings / suspected cause / preferred design / desired verdict" split — is stated in
`uacp-council/references/modes.md` (brainstorm-mode discipline). The *enum mechanism*
(`context_policy: minimal-non-leading` as a dispatch value) and its packet contract live in
`uacp-bridge/SKILL.md` + `uacp-debate/references/packet-contract.md`. This node's work is to **import that
enum into `uacp-council`'s review/audit dispatch**, which today has the discipline in prose but no
context-policy-aware dispatch machinery at all.

## The retain-vs-strip contract

For `context_policy: minimal-non-leading` on an external-reviewer dispatch:

**RETAIN (the engagement specification — the reviewer needs these to review the right thing):**

- `scope` — the artifact/paths under review.
- **The change specification** — a neutral pointer to *what changed*: the baseline ref + the diff
  (embedded in the prompt when the change is uncommitted, per the containment design), or the
  commit range under review. This is the fix for both starvation modes in [[01-narrative-vs-spec]].
- `task_type` / `mode` — these frame the *shape of the output* (findings vs proposals), not the
  conclusion; they stay.
- Hard constraints (read-only, no mutation, output contract).

**STRIP (the leading narrative — bias toward a conclusion):**

- Expected findings, suspected root cause.
- The author's / orchestrator's justification ("why this is correct"), self-assessment, checklist.
- Preferred design or architecture.
- Desired verdict.
- Other participants' prior findings (except where finding-driven mode deliberately supplies them —
  that is a different, explicitly-anchored mode and out of scope here).

The neutral change specification replaces the narrative `context_summary`, rather than blanking it.
Where a narrative field is stripped, the prompt must render an explicit non-leading instruction, never a
dangling empty label — the exact **rendering rule** is stated once in [[20-blast-radius]] (with the tests
that lock it); this node depends on it but does not restate it.

## Where it plugs in

- **`skills/uacp-bridge/SKILL.md`** — Input Schema + Agent Prompt Template: document that under
  `minimal-non-leading`, the `TASK:` / `CONTEXT:` lines carry the engagement spec (incl. the change
  pointer) and not the narrative; define the empty-narrative rendering rule.
- **`skills/uacp-council/references/phase-3-domain-planning.md`** — the prompt-injection table gains
  a policy-aware row: Tier 0/1 (in-runtime, same-model console review) keeps the full context; Tier
  >=2 external dispatch uses `minimal-non-leading` (retain scope + change spec + task_type/mode +
  constraints; strip narrative).
- **`skills/uacp-council/references/phase-4-dispatch.md` Step 6.2.3** — the `runtime_input` example
  carries `context_policy: "minimal-non-leading"` and a `change_spec` (baseline ref + diff pointer),
  with `context_summary` reduced to the neutral change specification, not blanked.

## Boundaries (avoid over-serialization)

This node states the *model and the retain/strip decision*. It deliberately does **not** pin field
names, the exact JSON shape of `change_spec`, or prompt wording — those are arbitrated at build by
tests ([[20-blast-radius]] specifies the tests that lock the behavior). The one hard invariant a
test must enforce: **an external `review`/`audit` dispatch never carries the leading narrative, and
always carries a resolvable change pointer.**

## Scope guard: Tier 0/1 untouched

The console review (Tier 0/1, in-runtime, same model as the author) is about role-coverage, not
independence — it was never the Deloitte case and keeps its full push context. The two paths are
separable because the `runtime_input` projection (Step 6.2.3) is the *only* place these fields cross
into an external runtime; Tier 0/1 build prompts directly from the in-runtime manifest. The
correctness of the split depends on editing **only the projection**, never the council manifest field
— see the projection-not-manifest rule in [[20-blast-radius]].
