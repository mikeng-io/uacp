# Adaptive Package Backfill Pattern

Use when a UACP run has already produced lifecycle YAML envelopes but the human-readable adaptive PROPOSE or PLAN package is missing.

## Signal

During artifact audit, you find only files such as:

- `proposals/{run_id}-proposal.yaml`
- `proposals/{run_id}-gate-selection.yaml`
- `plans/{run_id}-plan.yaml`
- `plans/{run_id}-scope.yaml`

…but no Markdown package directories:

- `proposals/{run_id}/`
- `plans/{run_id}/`

This is incomplete for medium/high-consequence or public/private/runtime-boundary work. YAML envelopes satisfy machine validators but are not the reviewable proposal/plan substance.

## Backfill procedure

1. State the gap plainly: Markdown proposal/plan packages are missing; YAML envelopes alone are insufficient.
2. Use existing authoritative artifacts as source of truth: triage, proposal, gate-selection, plan, scope, execution checkpoints, and verification audit.
3. Create package directories:
   - `proposals/{run_id}/`
   - `plans/{run_id}/`
4. Create concise Markdown modules, not one giant file.
5. Create bridge artifacts:
   - `proposals/{run_id}-package-selection.yaml`
   - `plans/{run_id}-plan-selection.yaml`
6. Mark the artifacts as `created_as: backfill` and record the backfill reason.
7. Continue lifecycle repair: PIV entries, transition artifacts, council synthesis, handled findings, final VERIFY.

## Minimal PROPOSE package modules

- `00-index.md`
- `proposal.md`
- `authority-scope-containment.md`
- `risks-and-verification.md`
- `artifacts.md`

These should cover: intent, authority, scope, containment, risk, verification, transition, artifact map.

## Minimal PLAN package modules

- `00-index.md`
- `plan.md`
- `work-packages.md`
- `authority-and-side-effects.md`
- `verification-strategy.md`
- `rollback-and-transition.md`

These should cover: work breakdown, dependencies, authority/side effects, tool/runtime selection, artifact write surfaces, verification strategy, rollback/recovery, council review topology, transition readiness.

## Pitfalls

- Do not claim “validator pass” means strict lifecycle completeness; validators may only check YAML envelopes.
- Do not bury the absence of Markdown packages under generic “artifact gaps.” Name the missing proposal/plan documents directly.
- Do not invent new scope while backfilling. Derive from existing authority artifacts and mark residual uncertainties explicitly.
- Do not restart or cross authority boundaries while performing documentation backfill.
