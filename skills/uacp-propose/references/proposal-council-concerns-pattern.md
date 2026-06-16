# Phase 6 Proposal Council Pattern — 2026-05-15

Use this reference when a UACP PROPOSE phase uses Agent Council and returns CONCERNS without blockers.

## Pattern

1. Record the proposal council as a `uacp.council_synthesis` artifact under `verification/`.
2. Patch the proposal and gate-selection artifacts before transition. Do not carry vague council feedback forward.
3. For each concern, classify as:
   - `resolved` — patched in proposal/gate/config/doc now.
   - `accepted_risk` — owner, residual risk, and condition recorded.
   - `deferred` — owner, target phase/run, and condition recorded.
4. Keep transient model/provider preferences out of canonical proposal doctrine. Put them in `operator_constraints`, runtime routing evidence, or current-session execution notes.
5. If council says the proposal duplicates existing doctrine, make PLAN start with a surface inventory/gap map before edits. Mark prior materials as `reuse`, `patch`, `defer`, or `out_of_scope`.
6. Validate artifacts before creating the PROPOSE→PLAN transition.
7. Run `uacp_heartgate_check`; only proceed on pass/warn with no blockers.

## Pitfalls caught

- Treating council CONCERNS as a clean pass without patching proposal/gate artifacts.
- Creating parallel doctrine when the actual gap is operationalization/tooling.
- Mixing phase-local council synthesis with Heartgate coherence artifacts.
- Hardcoding current delegate model names in canonical docs/config.
- Ignoring old plan sets that already cover part of the target design.

## Useful artifact shapes

- Phase-local council: `verification/<run>-proposal-council-synthesis-<date>.yaml`, kind `uacp.council_synthesis`.
- Transition artifact: references phase-local council via `council_synthesis_artifact`.
- Heartgate coherence: separate `heartgate_coherence.artifact_path` for transition-boundary coherence evidence when required.
