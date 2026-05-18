# Work Packages

## T1 — Skill doctrine
Patch `uacp-plan/SKILL.md` with adaptive PLAN package requirement, universal PLAN core, selected modules, N/A standard, envelope warning, and PLAN/EXECUTE boundary.

## T2 — Phase transition config
Patch `config/phase-transitions.yaml` with `adaptive_plan_package_gate` for PLAN→EXECUTE and PLAN exit invariants for selected package artifacts.

## T3 — Validator
Patch `scripts/validate_uacp_artifacts.py` to validate `kind: uacp.plan_package_selection`.

## T4 — Heartgate kernel
Patch `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` to enforce adaptive PLAN package gate for PLAN→EXECUTE.

## T5 — Guardian policy
Patch `config/guardian-policy.yaml` so PLAN package directories and envelopes are recognized under UACP artifacts.

## T6 — Fixtures
Create `verification/fixtures/adaptive-plan-package/` with pass, block, missing-package, and yaml-only fixtures.

## T7 — Verification and council
Run validator/Heartgate checks, then focused council over actual diffs/evidence.
