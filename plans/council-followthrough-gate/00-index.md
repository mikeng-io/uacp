# Council Follow-Through Gate — PLAN Index

Run: `council-followthrough-gate-20260514-201718`
Phase: PLAN
Status: draft for PLAN council

## Objective

Convert the approved/provisionally adopted proposal into bounded EXECUTE work for a UACP gate that prevents handled negative Agent Council findings from silently becoming phase-transition passes.

## Inputs

- TRIAGE: `state/runs/council-followthrough-gate-20260514-201718-triage.yaml`
- TRIAGE council: `verification/council-followthrough-gate-triage-council-synthesis-20260514.yaml`
- TRIAGE→PROPOSE transition: `verification/council-followthrough-gate-triage-to-propose-20260514.yaml`
- PROPOSE: `proposals/council-followthrough-gate-20260514-201718.yaml`
- PROPOSE gate-selection: `proposals/council-followthrough-gate-20260514-201718-gate-selection.yaml`
- PROPOSE council: `verification/council-followthrough-gate-propose-council-synthesis-20260514.yaml`
- PROPOSE→PLAN transition: `verification/council-followthrough-gate-propose-to-plan-20260514.yaml`

## PLAN package

- `00-index.md` — this file
- `01-surface-inventory.md` — docs/config/validator/skill surfaces and disposition
- `02-requirements-and-design.md` — exact doctrine/config behavior to implement
- `03-execution-plan.md` — bounded execution work packages and write surfaces
- `04-verification-and-resolution.md` — positive/negative/regression checks and closure criteria

## Key PLAN decisions

1. Implement the follow-through gate as a lifecycle/transition rule, not as a separate lifecycle phase.
2. Keep the gate adaptive: material findings trigger follow-up council; trivial findings do not.
3. Preserve Agent Council / Heartgate separation: council supplies evidence, Heartgate decides transition legitimacy.
4. Add explicit TRIAGE-local council/Heartgate trigger policy for high-granularity governance-core admission, because Mike corrected that TRIAGE and PROPOSE must not be compressed.
5. Use governed writers for canonical docs/config changes in EXECUTE.

## PLAN exit criteria

Before PLAN→EXECUTE:

- PLAN council synthesis exists and has no unresolved blockers.
- Any PLAN council concerns are patched into this package or carried as owned warnings/deferred items.
- Artifact validation passes.
- PLAN→EXECUTE transition exists and `uacp_heartgate_check` passes or passes with accepted warnings.
