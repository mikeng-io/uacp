# Phase 4B Resolve Lessons — Contained Shell Seam

Use this reference when closing UACP runtime/containment phases or resolving a phase after Agent Council returns concerns that are accepted as hardening follow-ups.

## Durable lessons

### Heartgate enum discipline

Heartgate transition artifacts may reject non-canonical status/state values such as `pass_with_concerns` inside `invariant_summary[].status` or `cluster_summary[].state`.

Preferred shape:

- Set invariant/cluster status to `pass` when the phase can close.
- Carry the concern text in `warnings` and `deferred_items` with owner, residual risk, `accepted_by`, and a concrete condition.
- Keep `blockers: []` only when the concern is genuinely non-blocking.

This preserves strict transition validation while avoiding the false implication that council concerns were ignored.

### Contained shell boundary

`uacp_contained_shell` is a governed contained execution seam, not a general-purpose bypass for mutating `UACP_ROOT`.

During Phase 4B closure, invoking it with `workspace=/home/norty/.hermes/uacp` correctly failed containment verification because:

- execution workspace is under `UACP_ROOT`
- `UACP_ROOT` is under execution workspace

For UACP-root writes, continue using governed writers:

- `uacp_state_write` for `state/`
- `uacp_artifact_write` for verification/output artifacts
- `uacp_doc_write` for canonical docs
- `uacp_config_write` for config

Use `uacp_contained_shell` for contained execution in a separate workspace that can be made writable while `UACP_ROOT` remains read-only.

### Closure evidence pattern

For runtime phase closure:

1. Create `verify-to-resolve` transition with full schema fields.
2. Run `uacp_heartgate_check` before updating run/current state.
3. If Heartgate blocks on status vocabulary, rewrite to canonical `pass` + warnings/deferred items, not looser status strings.
4. Update run manifest to `phase: resolve` and a precise resolved status.
5. Update `state/current.yaml`.
6. Write a resolution artifact under `verification/` with:
   - closure evidence
   - resolved invariants
   - repository hygiene
   - rollback
   - carried-forward hardening
   - side effects performed/not performed
7. Re-run the live proof harness after state closure when the phase changed runtime behavior.

## Hardening items that should carry forward after Phase 4B

- Bounded stdout/stderr capture for contained shell.
- Host read exposure threat model and possible narrower bind mounts.
- Attestation lifecycle cleanup/persistence only if restart continuity becomes necessary.

## What not to persist as doctrine

Do not encode the transient failure of a particular command invocation as "contained shell does not work." The durable rule is the boundary: contained shell needs a separate workspace and should not be used as the writer path for `UACP_ROOT` mutation.
