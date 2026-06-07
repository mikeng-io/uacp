# UACP Operational Dashboard And Live Proof

Use this note when UACP has live runtime adapter bindings and the next session needs a compact, verified re-entry point instead of rediscovering status from scattered docs/logs.

## Pattern

After runtime binding or cleanup work, create two durable surfaces:

1. `UACP_ROOT/..outputs/uacp-operational-dashboard.yaml`
   - current UACP operational status,
   - live adapter bindings and source/binding paths,
   - open blockers with severity,
   - ordered next actions,
   - repository and approval policy,
   - deferred side threads such as compression diagnostics.

2. `UACP_ROOT/scripts/live_guardian_probe.py` plus `verification/live-guardian-proof-<date>.yaml`
   - a non-destructive proof harness that can be rerun after restart/cleanup,
   - records proof that live bindings still resolve and load.

## Safe live proof checks

The first safe probe should verify only non-destructive facts:

- UACP-owned adapter source exists under `runtime-adapters/hermes/plugins/<plugin>/`.
- `HERMES_ROOT/plugins/<plugin>` is a symlink to the UACP source.
- plugin manifests exist.
- `HERMES_ROOT/config.yaml` enables the expected plugins.
- `hermes plugins list` reports expected plugins as `enabled` and `source=user`.
- key UACP YAML files parse.
- removed temporary probe/duplicate Hermes plugin paths remain absent.

Avoid mutating config, state, remotes, or protected paths from the safe probe.

## Session-proven artifact set

For the live Hermes UACP adapter checkpoint, the useful artifacts were:

- `..outputs/uacp-operational-dashboard.yaml`
- `scripts/live_guardian_probe.py`
- `verification/live-guardian-proof-20260514.yaml`

The proof harness emitted YAML and the verification artifact was committed/pushed to the private UACP remote after passing.

## Approval/authority convention

Mike approved UACP continuation with a broad local execution boundary: local UACP edits, local tests/proofs, local commits, and UACP private pushes can proceed when they are the natural next step and do not weaken security. Do **not** push the Hermes Agent upstream repo; keep Hermes Agent local patch consolidation local unless an explicit upstream PR workflow is requested.

## Pitfalls

- Do not treat `hermes plugins list` alone as sufficient; also verify symlink targets and YAML parse.
- Do not let the dashboard become a second source of truth. It is a compact pointer to canonical docs/config/status and must be updated after verified changes.
- Keep live-proof scripts safe by default; put destructive/containment tests behind a separate explicit mode later.
