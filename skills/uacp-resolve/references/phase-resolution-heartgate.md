# UACP phase resolution + Heartgate schema notes

Use this reference when closing an EXECUTE-stage UACP run after implementation and Agent Council review are already complete.

## Durable closure pattern

1. Verify current reality first:
   - live proof/probe result
   - council synthesis result
   - cleanup/status docs reflect actual bindings and deferred risks
2. Create a compact `verification/*resolve-readiness*.yaml` artifact.
3. Create `state/runs/*execute-to-verify-transition.yaml` and run `uacp_heartgate_check`.
4. Create `state/runs/*verify-to-resolve-transition.yaml` and run `uacp_heartgate_check`.
5. Mark plan/run manifest resolved only after Heartgate returns pass/warn with no blockers.
6. If continuing immediately, create the next run's TRIAGE artifact and run manifest, then update `state/current.yaml`.

## Heartgate metadata that must be present

Deferred item shape:

```yaml
deferred_items:
  - id: runtime_execution_seam_absent
    owner: next_phase
    accepted_by: Mike current private control prompt to continue next phase
    condition: Design/prove a contained execution seam before enabling shell/code.
```

Warning shape:

```yaml
warnings:
  - id: phase4_evidence_only_closure
    owner: next_phase
    residual_risk: Phase resolved as evidence-only; standard shell/code remain blocked until a contained execution seam is designed and verified.
```

Avoid plain string warnings when Heartgate expects owned accepted-warning metadata.

## Evidence-only closure wording

For governance/runtime phases, explicitly say what changed and what did **not** change. Example:

- Implemented: evidence checker/proof harness/council review.
- Not enabled: standard terminal/execute_code allow path.
- Deferred: real contained execution seam with proof and council before any allow-path claim.

This prevents a successful evidence phase from being mistaken for a permission grant.
