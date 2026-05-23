# Retrieval-Led VERIFY Pattern for Governance Runs

Use this reference when a UACP VERIFY phase must prove that Agent Council, Heartgate, artifact-schema, validator, or governance/runtime changes are grounded in actual repository state rather than coordinator summary.

## Trigger

Use this pattern when VERIFY follows a phase that changed any of:

- Agent Council doctrine or output contracts
- Heartgate transition requirements or coherence evidence
- artifact schemas or validators
- Guardian/runtime/governed writer behavior
- lifecycle state, run manifests, or dashboard/status artifacts
- skill alignment that affects UACP execution but lives outside the UACP repo

## Sequence

1. **Run deterministic checks first**
   - Use contained shell for read-only validation.
   - Prefer `PYTHONDONTWRITEBYTECODE=1` plus AST parsing for Python syntax checks.
   - Explicitly pass the artifacts you care about to `scripts/validate_uacp_artifacts.py`; do not assume auto-discovery exists unless the validator implements it.

2. **Validate council synthesis artifacts explicitly**
   - Include current proposal/plan/execute/verify council synthesis artifacts in the validator command.
   - Confirm `kind: uacp.council_synthesis` artifacts have non-empty `inspected_paths`.
   - Treat "validator checks only artifacts it was given" as an accepted residual only if the explicit artifact list covers the run's current evidence.

3. **Check Heartgate artifact separation**
   - `council_synthesis_artifact` should reference phase-local council evidence.
   - `heartgate_coherence.artifact_path` should reference transition-boundary coherence evidence or a dual-scope artifact that explicitly covers Heartgate lenses.
   - Verify the required lenses are present when `heartgate_coherence` exists.

4. **Ground-truth out-of-repo dependencies**
   - If VERIFY claims skill alignment, inspect the actual skills through `skill_view` and record that the skill store is outside the UACP repo commit boundary.
   - Do not imply those skill changes are committed in the UACP repo unless they are mirrored there.

5. **Run VERIFY council after deterministic checks**
   - Dispatch role-diverse reviewers with direct file paths and commands to inspect.
   - Require file/path evidence and explicit PASS/CONCERNS/FAIL.
   - Synthesize a `kind: uacp.council_synthesis` artifact with `inspected_paths`.

6. **Carry only honest residuals to RESOLVE**
   - Resolved items should name evidence.
   - Accepted risks need owner and condition.
   - Deferred items need future owner/trigger and must not be claimed active.

## Minimal VERIFY artifact fields

Record:

- command surface and containment mechanism
- write probe status
- syntax parse result for changed Python files
- exact validator command or artifact list
- `RESULT PASS|WARN|BLOCK`
- council synthesis artifact paths
- skill alignment status, including whether skills are outside repo
- remaining accepted risks and deferred items

## Common pitfalls

- Claiming "all artifacts validated" when only synthesis/transition artifacts were passed to the validator.
- Treating a phase-local council artifact as Heartgate coherence without the required Heartgate lenses.
- Claiming skill alignment without inspecting the loaded skill body.
- Forgetting to disclose that skill updates live outside the UACP repo and therefore are not included in UACP git commits.
