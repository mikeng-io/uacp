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

## L2 — rework-cap adjudication vs. discharge semantics (Codex #173 P1) — RULED

In `engines/rework_completeness.py`, at/above `max_rework_depth` a carried finding with a **complete
adjudication** (decision + rationale + cost-if-wrong) may still emit an ordinary
`RW_CARRIED_FINDING_*` blocker, because `discharged` is keyed on `_disposition_complete` +
`_disposition_defects`, independent of `_adjudication_complete`.

**Ruling** (cross-provider audit, Kimi, reading the code): this is **intended strictness, not a
liveness bug.** A canonically well-formed accepted-exception entry *automatically* satisfies
`_disposition_complete` (well-formedness requires `residual_risk` for carry-forward classes). So for an
accepted-exception (`deferred`) entry, the only adjudication-complete-but-not-discharged state is a
complete adjudication sitting on a *structurally malformed* canonical item (a remediation-class entry
can also fail discharge via a non-resolving `handling_artifact_path`, but that is not L2's case) — and the escape is **completing the canonical fields**
(`heartgate_validation`, `next_phase_obligation`, …), i.e. record-completion, not remediation. This is
consistent with `#149` fail-closed-on-malformed-disposition. It is not a deadlock.

- **Materiality:** the cap codes are **block**-severity (`RW_REWORK_CAP_UNADJUDICATED` is hardcoded
  `block`; the `RW_CARRIED_FINDING_*` codes default to `block`) — so this is NOT dismissible as
  "warn-advisory" (an earlier draft of this node wrongly said the breaker was warn-by-default; it is
  not). It is **non-material by FAILURE DIRECTION**: the behavior over-enforces (at worst it demands a
  complete record before closing), it never lets a finding close silently. A defect that fails toward
  over-enforcement is non-material per Invariant #4; that — not a (false) warn severity — is why it is
  safe to ship.
- **Disposition:** `justified` (confirmed intended behavior). No code change owed.
- **Follow-on (doc-drift, not a code blocker):** `03-enforcement-and-loop.md:31` describes discharge
  as "complete … *or* adjudicated" — an OR the code implements as AND-at-the-cap. Correct that line to
  match the ruled behavior.

## Why these merge without a council-gate violation

Key Invariant #5 ("evidence must be produced") and the council gate ("zero material findings
unresolved") are satisfied: each finding is **dispositioned** (L1 `deferred`, L2 `justified`, both
with rationale + residual risk + follow-on) — the framework's own `handled_findings_chain` resolution.
Crucially, **neither is material**, so neither needs the independent countersignature that Invariant
#4 now requires for deferring a *material* finding:

- **L1** — non-material because it fails toward *under-nudging* only within a **warn** advisory gate
  (weakens a nudge, cannot bypass a hard gate).
- **L2** — block-severity, but non-material by **failure direction**: it over-enforces, never closes
  silently. Materiality is about *failure direction and stated guarantees*, not severity alone — an
  earlier draft mis-grounded L2 on a (false) warn severity; corrected above.

Had either been material (a defect failing toward *under*-enforcement — a gate bypass), adjudication
alone would NOT resolve it: Invariant #4 requires a fix or a deferral countersigned by an authority
independent of the author. See node `11` for the invariant wording and the audit that produced it.
