# Operational Dashboard and Live Proof

Use this note when UACP has live runtime adapter bindings and the next session needs a compact, verified re-entry point instead of rediscovering status from scattered docs/logs.

## Two-Surface Pattern

After runtime binding or cleanup work, create two durable surfaces:

**Surface 1: `UACP_ROOT/.outputs/uacp-operational-dashboard.yaml`**
- current UACP operational status
- live adapter bindings and source/binding paths
- open blockers with severity
- ordered next actions
- repository and approval policy
- deferred side threads (e.g., compression diagnostics)

**Surface 2: `UACP_ROOT/scripts/live_guardian_probe.py` plus `verification/live-guardian-proof-<date>.yaml`**
- a non-destructive proof harness that can be rerun after restart/cleanup
- records proof that live bindings still resolve and load

## 7-Item Safe Probe Checklist

The first safe probe should verify only non-destructive facts:

1. UACP-owned adapter source exists under `runtime-adapters/<runtime>/plugins/<plugin>/`.
2. `<RUNTIME_ROOT>/plugins/<plugin>` is a symlink to the UACP source.
3. Plugin manifests exist.
4. Runtime `config.yaml` enables the expected plugins.
5. `<runtime> plugins list` reports expected plugins as `enabled` and `source=user`.
6. Key UACP YAML files parse without errors.
7. Removed temporary probe/duplicate plugin paths remain absent.

Avoid mutating config, state, remotes, or protected paths from the safe probe.

## Approval/Authority Convention

Local UACP edits, local tests/proofs, local commits, and UACP private pushes can proceed when they are the natural next step and do not weaken security. Do **not** push host-runtime upstream repos; keep host-runtime local patch consolidation local unless an explicit upstream PR workflow is requested.

## Pitfalls

- Do not treat a plugin list command alone as sufficient; also verify symlink targets and YAML parse.
- Do not let the dashboard become a second source of truth. It is a compact pointer to canonical docs/config/status and must be updated after verified changes.
- Keep live-proof scripts safe by default; put destructive/containment tests behind a separate explicit mode later.
