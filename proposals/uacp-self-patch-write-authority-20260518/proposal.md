# UACP Self-Patch Write Authority — Proposal

## Objective
Define a narrow governed exception for UACP self-patches that touch skill exports, validator scripts, and runtime-adapter source when no governed writer currently reaches those paths.

## Problem
Heartgate correctly blocks PLAN->EXECUTE when `scope.write_paths` include paths unreachable by execute-phase governed writer tools. The adaptive PLAN run exposed this for:

- `skills/devops/uacp/uacp-plan/SKILL.md`
- `scripts/validate_uacp_artifacts.py`
- `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py`

## Proposed repair
Add an explicit `self_patch_write_authority` block to scope artifacts. Heartgate may accept otherwise-unreachable paths only when all are true:

1. `enabled: true`
2. `reason`, `authority_artifact`, `owner`, `rollback_path`, and `verification_obligations` are present.
3. The path matches a tight allowed prefix:
   - `skills/devops/uacp/`
   - `scripts/`
   - `runtime-adapters/`
4. The run is high-governance UACP self-repair, not an ordinary implementation run.

## Non-goal
Do not add `terminal` or generic patch as a universal UACP writer capability.

## Verification
- Add kernel validation for `self_patch_write_authority`.
- Patch the adaptive PLAN scope with explicit authority block.
- Rerun Heartgate PLAN->EXECUTE check.
