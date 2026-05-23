# UACP Phase 4 Filesystem Containment Start Pattern — 2026-05-13

Use this reference when starting a security-sensitive UACP runtime containment phase, especially work that may move shell/code execution from fail-closed-only toward allowed-with-evidence.

## Session-proven sequence

1. Load UACP lifecycle skills and rehydrate current state from artifacts, not chat memory alone.
2. Create a TRIAGE artifact under `state/runs/` before writing a proposal.
3. Create a bounded PROPOSE artifact and a PROPOSE gate-selection artifact.
4. Run a focused tier-2 Agent Council before implementation. Use role-diverse review:
   - Security/Guardian reviewer
   - Runtime/filesystem isolation reviewer
   - Lifecycle/verification reviewer
5. Record a formal council synthesis artifact under `verification/`.
6. Write a propose→plan transition artifact and run `uacp_heartgate_check` before accepting PLAN.
7. If Heartgate blocks on warnings/deferred items, rewrite the transition so that:
   - `warnings` are structured maps with `owner` and `residual_risk`
   - warned cluster artifact paths appear in `accepted_exceptions` with `artifact_path`, `rationale`, and `owner`
   - each `deferred_items` entry has `cluster_id`, `owner`, `condition`, and `accepted_by`
8. Create the PLAN artifact and PLAN gate-selection artifact only after the transition is accepted/pass-or-warn.
9. Update `state/current.yaml` through `uacp_state_write` after the Heartgate-checked transition.
10. Commit the UACP artifact checkpoint locally before implementation.

## Council constraints that should block EXECUTE if unresolved

- A concrete containment mechanism is named, not just “sandbox” or “read-only check”.
- `filesystem_guard_verified` is never self-attested by prompt/context alone.
- `uacp_sandbox_check` or equivalent evidence is required for any allow decision.
- Terminal and `execute_code` have separate backend-specific containment proofs.
- Verification includes symlink-aware path checks, mount/read-only inspection where applicable, and a real write probe from the execution context.
- Non-standard plugin dispatch, slash commands, and control-plane paths are explicitly out of scope or blocked.
- Evidence has TTL/invalidation rules and rollback forces fail-closed.

## Heartgate artifact pitfall

Heartgate treats free-text warnings and incomplete deferred items as blockers. Use structured warnings/deferred records rather than prose lists when crossing a phase boundary.

Minimal shape:

```yaml
warnings:
  - owner: main_session
    residual_risk: PLAN may still fail if containment cannot be proven.
    next_phase_acceptance: PLAN must convert this into hard EXECUTE requirements.
deferred_items:
  - id: concrete_containment_mechanism
    cluster_id: filesystem_containment_design
    owner: main_session
    condition: PLAN names concrete mechanism and verification evidence.
    accepted_by: plan
accepted_exceptions:
  - artifact_path: verification/<council-synthesis>.yaml
    rationale: Council concerns are accepted as next-phase requirements.
    owner: main_session
```
