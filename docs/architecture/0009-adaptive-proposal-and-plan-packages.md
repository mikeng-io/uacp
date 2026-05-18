# ADR 0009: Adaptive PROPOSE and PLAN Documentation Packages

Status: accepted
Date: 2026-05-18

## What changed

UACP now treats medium/high-consequence PROPOSE and PLAN work as human-reviewable documentation packages instead of single YAML envelopes.

The committed change set adds:

- `adaptive_proposal_package_gate` in `config/phase-transitions.yaml`.
- `adaptive_plan_package_gate` in `config/phase-transitions.yaml`.
- Guardian/Heartgate enforcement for `PROPOSE -> PLAN` package-selection artifacts and package directories.
- Guardian/Heartgate enforcement for `PLAN -> EXECUTE` plan-selection artifacts, plan package directories, and scope artifacts.
- Validator support for `uacp.proposal_package_selection` and `uacp.plan_package_selection` artifacts.
- Guardian policy wording that explicitly allows adaptive package directories and top-level machine lifecycle envelopes as non-state UACP artifacts.
- Fixture artifacts for passing and blocking adaptive package-selection cases.
- Lifecycle artifacts from the 2026-05-18 adaptive documentation work, including proposal, plan, execution, verification, resolution, gate-ledger, and LEXA/SEF output packages.

## Why we are changing it

Single YAML lifecycle envelopes were becoming too compressed for serious UACP work. They can record phase state, but they are not sufficient as the whole review surface for governance/runtime changes, public-private boundary work, validator changes, or complex design work.

The rational intent is to preserve UACP's lifecycle discipline while letting each phase choose documentation granularity locally:

- PROPOSE decides how much human-readable proposal documentation is needed for intent, authority, scope, containment, risk, verification, transition readiness, and artifact mapping.
- PLAN decides how much execution topology documentation is needed for work breakdown, dependencies, authority/side effects, runtime/tool selection, write surfaces, verification strategy, rollback, council review, and transition readiness.
- YAML artifacts remain lifecycle envelopes and machine bridges; they do not replace the package that reviewers and future agents must inspect.

This prevents the failure mode where a high-consequence governance change is technically represented by a small YAML file but lacks reviewable rationale, boundaries, invariants, and evidence.

## Invariants

The following invariants are intentional and must be preserved:

1. UACP remains adaptive and generic. The package gates must not hard-code Trustless ACP/OpenSpec-specific document lists or domain assumptions.
2. Granularity is phase-local. TRIAGE/PROPOSE/PLAN may inform downstream work, but no earlier phase permanently fixes all later documentation topology.
3. YAML lifecycle artifacts are envelopes. For selected medium/high-consequence work, the package directory is the primary human review surface.
4. Package-selection artifacts are mandatory when the adaptive gate applies. They are the machine-readable bridge between phase intent and package contents.
5. Selected modules must name their rationale and artifact path. Missing rationale or missing files are blockers, not warnings.
6. Universal core concerns must be either `covered` with an artifact path or `not_applicable` with explicit reason, acceptance, owner, residual risk, and revisit information.
7. PLAN packages require a scope artifact. Scope is separate from the plan package to keep authority and execution boundary checks machine-visible.
8. Guardian/Heartgate and the standalone validator must enforce the same minimum package semantics.
9. Negative fixtures are allowed to fail validation when intentionally passed to the validator; they exist to prove the validator catches missing package-selection semantics.
10. Artifact writes remain non-state writes unless they target governed state paths. Runtime state is still owned by the governed state mutation boundary.
11. The active Hermes skill export and canonical UACP repo remain separate surfaces. A repo validation pass does not prove live skill exports have been refreshed.
12. LEXA/SEF/SGRN documents in `outputs/semantic-event-fabric-2026-05-17/` are design-output artifacts, not UACP runtime state and not a claim that those systems have been implemented.

## Enforcement details

Heartgate now checks:

- `proposals/{run_id}-package-selection.yaml` for `PROPOSE -> PLAN` transitions.
- `proposals/{run_id}/` for selected proposal package directories.
- `plans/{run_id}-plan-selection.yaml` for `PLAN -> EXECUTE` transitions.
- `plans/{run_id}/` for selected plan package directories.
- `plans/{run_id}-scope.yaml` for PLAN scope boundary evidence.
- `universal_core` entries for required concerns.
- `selected_modules` for explicit reason and existing artifact paths.
- `not_applicable` entries for accountable rationale and revisit fields.

The standalone validator mirrors these checks for manual drills and repository-level validation.

## Operational notes

- Use normal Git workflow for UACP self-modification; do not rely on broken or under-review UACP protected writers to approve their own changes.
- Validate config-only coherence with `python scripts/validate_uacp_artifacts.py --root .`.
- Validate specific artifacts by passing explicit YAML paths. Do not bulk-pass intentional negative fixtures unless the expected result is `BLOCK`.
- Commit messages for governance changes must name what changed, why it changed, and the invariants/verification state.
