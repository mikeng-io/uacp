# Adaptive Proposal Package Enforcement — 2026-05-18

Use this reference when repairing or applying UACP PROPOSE composition for medium/high consequence work.

## Core lesson

A serious UACP proposal is a **human-reviewable package**, not a single YAML document.

- `proposals/{run_id}/` is the review package.
- `proposals/{run_id}-proposal.yaml` is only the machine lifecycle envelope.
- `proposals/{run_id}-package-selection.yaml` is the machine bridge from package concerns to validator/Heartgate gates.

Do not regress to `proposal.yaml = whole proposal`. If top-level YAML exports are needed for validator/Heartgate compatibility, label them as envelopes and point to the package directory.

## Required package-selection shape

For selected medium/high consequence work, `package-selection.yaml` should encode:

- `kind: uacp.proposal_package_selection`
- `phase: propose`
- `run_id`
- `work_heart.primary` and optional secondary domains
- `universal_core` coverage for:
  - `intent`
  - `authority`
  - `scope`
  - `containment`
  - `risk`
  - `verification`
  - `transition`
  - `artifact_map`
- `selected_modules` with `reason` and `artifact`
- `not_applicable` entries with:
  - `reason`
  - `accepted_by`
  - `owner`
  - `residual_risk`
  - `revisit_phase`

## Enforcement surfaces

A complete repair should wire the doctrine into all relevant layers:

1. `uacp-propose` skill + references.
2. `config/phase-transitions.yaml` with `adaptive_proposal_package_gate`.
3. `scripts/validate_uacp_artifacts.py` recognition of `uacp.proposal_package_selection`.
4. `config/guardian-policy.yaml` artifact classification for package directories and envelope YAMLs.
5. Heartgate/kernel-level PROPOSE→PLAN check, not just prose/config.
6. Pass/block fixtures.
7. VERIFY evidence showing positive and negative gate behavior.

## Heartgate behavior to prove

A positive PROPOSE→PLAN dry-run should pass when package-selection and package directory exist and selected artifacts are present.

A negative fixture should block and include an `adaptive_proposal_package_gate` blocker when package-selection is missing or incomplete.

If the live plugin/tool may cache old code, verify the edited kernel/module directly and record a runtime reload note before relying on live enforcement in later sessions.

## Pitfalls

- Do not select proposal docs from granularity alone; granularity scales rigor, the work-heart selects modules.
- Do not require fixed OpenSpec filenames when concerns are covered by context-appropriate documents.
- Do not let council synthesis or gate-selection YAML substitute for the proposal package.
- Do not proceed to PLAN with missing selected concerns unless there is explicit not-applicable rationale with owner and residual risk.
