---
type: design
title: "Floor known limitations — accepted residual (advisory-gate gaps, adjudicated not fixed)"
description: "The M1-M5 floor gates are warn-level advisory checks. Adversarial review will always surface edge cases in gate logic (that is the non-convergence documented in node 09). This node ADJUDICATES the residual findings as accepted non-goals with rationale + severity — the disposition that lets the floor merge without chasing findings to zero. A finding is RESOLVED when fixed OR adjudicated; these are adjudicated."
tags: [grounded-governance, floor, known-limitations, accepted-residual, adjudication, stop-rule]
timestamp: "2026-08-27"
edges: [{dst: 09-the-reckoning-verify-is-run-not-built, rel: extends, provenance: asserted}]
---
# Floor known limitations — accepted residual

The M1-M5 floor gates are **warn-level advisory** checks (config-gated `warn`→`block`; default `warn`).
Per node `09`, grounding-as-gate-logic never reaches zero findings under adversarial review — an
edge case always remains. "Done" therefore cannot mean "the reviewer is silent"; it means **the
residual is adjudicated** (accepted, with rationale, at a severity that does not break a stated
guarantee). These are that adjudication. They are RESOLVED by disposition, not by fix.

## L1 — behavioral-floor code detection uses a closed suffix allowlist (Codex #173 P2)

`_CODE_SUFFIXES` in `engines/manifest/projection.py` is a fixed list; source changed in a language
outside it (`.cs`, `.kt`, `.php`, `.swift`, `.ex`, `.vue`, extensionless scripts) is classified as
documentation-only and does not raise `CHK_BEHAVIORAL_FLOOR_UNMET`.

- **Severity / disposition:** `deferred` (accepted non-goal). The behavioral floor is a **warn**
  advisory; a missed language weakens a nudge, it does not bypass a hard gate. A closed allowlist is
  inherently incomplete — completeness is unreachable, not merely unimplemented.
- **Residual risk:** a code change in an unlisted language does not get nudged toward a behavioral
  check. Bounded: the diff-coverage / evidence-resolves floors (M2/M3c) still apply.
- **Follow-on (not a blocker):** replace the allowlist with a conservative classifier — treat any
  non-document change as code (fail-toward-nudge) — when the behavioral floor is promoted to `block`.

## L2 — rework-cap adjudication vs. discharge semantics (Codex #173 P1)

In `engines/rework_completeness.py`, at/above `max_rework_depth` a carried finding with a **complete
adjudication** (decision + rationale + cost-if-wrong) may still emit an ordinary
`RW_CARRIED_FINDING_*` blocker, because `discharged` is keyed on `_disposition_complete` +
`_disposition_defects`, independent of `_adjudication_complete`. Whether this is an over-block (the
cap escape-hatch of `03-enforcement-and-loop.md:29-32` should let a complete adjudication close) or
intended strictness (an adjudication must ALSO be a well-formed disposition record) is a genuine
**design-semantics ambiguity**, not a settled bug.

- **Severity / disposition:** `deferred` (accepted non-goal, pending a design ruling). It bites only
  when BOTH the rework cap is hit AND a finding is adjudicated-but-not-remediated — a narrow corner —
  and the cap breaker is itself **warn** by default.
- **Residual risk:** at the cap, an adjudicated-not-remediated finding may fail to close, forcing
  actual remediation. This fails **toward** strictness (over-block), not toward silent closure — the
  safe direction for a governance gate.
- **Follow-on (not a blocker):** a dedicated round to rule on whether `_adjudication_complete` grants
  discharge at the cap, and align the code with `03:29-32` either way.

## Why these merge without a council-gate violation

Key Invariant #5 ("evidence must be produced") and the council gate ("zero material findings
unresolved") are satisfied here: each finding above is **dispositioned** (`deferred`, with rationale
+ residual risk + follow-on) — the framework's own `handled_findings_chain` resolution, not a fix.
"Material" is severity-relative: a **warn** advisory gate's edge-case gap is not a material finding.
See node `11` (proposed AGENTS.md refinement) for making that reading explicit in the invariant.
