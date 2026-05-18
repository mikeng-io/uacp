# Surface Inventory

## Patch
- `/home/norty/.hermes/skills/devops/uacp/uacp-plan/SKILL.md` — add adaptive PLAN package doctrine and output contract.
- `config/phase-transitions.yaml` — add adaptive PLAN package gate for PLAN→EXECUTE.
- `scripts/validate_uacp_artifacts.py` — add `kind: uacp.plan_package_selection` validation.
- `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py` — add PLAN→EXECUTE package gate logic.
- `config/guardian-policy.yaml` — recognize PLAN package artifacts as UACP artifacts.
- `verification/fixtures/adaptive-plan-package/` — add pass/block/missing/yaml-only fixtures.

## Reuse
- Existing adaptive PROPOSE package gate model in `phase-transitions.yaml`, validator, kernel, and fixtures.
- Existing PLAN_VALIDATION ledger contract.

## Defer
- Live runtime plugin reload / restart proof; VERIFY must record caveat or perform proof if available.
- EXECUTE/VERIFY/RESOLVE package refactors.

## Out of scope
- LEXA.
- External pushes/PRs.
- Trustless ACP/OpenSpec structure import.

## Current scan evidence
- `phase-transitions.yaml` contains `adaptive_proposal_package_gate`, not adaptive PLAN package gate.
- validator contains `proposal_package_selection`, not `plan_package_selection`.
- Heartgate kernel contains proposal package gate logic, not PLAN package gate logic.
- `verification/fixtures/adaptive-plan-package/` does not yet exist.
- `docs/lifecycle-reference.md` and `docs/orchestration-model.md` are absent in this local UACP root; do not patch missing docs.
