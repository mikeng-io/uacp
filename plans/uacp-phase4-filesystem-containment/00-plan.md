# UACP Phase 4 — Filesystem Containment Plan

Run ID: `uacp-phase4-filesystem-containment-20260513-215531`
Phase: `RESOLVE`
Status: completed — evidence-only containment phase resolved on 2026-05-14.

## Objective

Enable UACP-bound `exec.shell` and `exec.code_with_tool_proxy` only when the runtime can prove filesystem containment. The default remains fail-closed.

## Resolution outcome

Phase 4 implemented and verified `uacp_sandbox_check` as a containment evidence checker. It proves that the local host can run a bwrap read-only-root probe that blocks writes to `UACP_ROOT` while keeping a sandbox workspace writable.

Phase 4 deliberately did **not** enable the standard Hermes `terminal` or `execute_code` paths. Those paths remain fail-closed for UACP-bound shell/code execution until a real contained execution seam exists.

Resolution artifacts:

- `verification/phase4-resolve-readiness-20260514.yaml`
- `verification/uacp-phase4-sandbox-check-post-implementation-council-20260513.yaml`
- `state/runs/uacp-phase4-filesystem-containment-20260513-execute-to-verify-transition.yaml`
- `state/runs/uacp-phase4-filesystem-containment-20260513-verify-to-resolve-transition.yaml`

## Authority and boundaries

- Authority: Mike explicitly requested Phase 4 start in the private control session and later authorized continuing if completion checks passed.
- UACP declares required posture and evidence obligations.
- Guardian verifies runtime-provided evidence inside the controlled tool path.
- Host/runtime supplies real containment.
- Manual/operator-side edits remain out-of-band and untrusted until revalidated.
- No upstream Hermes Agent push or PR was performed in this phase.
- No broad shell/code enablement was performed.

## Council constraints accepted into PLAN

The focused Agent Council returned `concerns`, not `fail`. The following were accepted as hard requirements before EXECUTE:

1. Name a concrete containment mechanism.
2. Make `uacp_sandbox_check` or equivalent evidence generation required for allow decisions.
3. Define terminal and `execute_code` separately; block `execute_code` if backend containment cannot be proven.
4. Include symlink-aware path resolution, mount/read-only inspection where applicable, and actual write-probe failure from execution context.
5. Scope allow behavior to standard guarded Hermes tool-call paths; non-standard plugin dispatch/slash/control-plane paths stay out of scope or blocked.
6. Define evidence TTL/invalidation and rollback to fail-closed.
7. Generate PLAN-phase gate selection and Heartgate-check PLAN→EXECUTE transition before implementation.

All applicable evidence-checker requirements were satisfied. The positive allow-path candidate was explicitly deferred because no real contained execution seam exists yet.

## Implemented shape

### Target files

- `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py`
  - Added containment path relationship helper.
  - Added bwrap read-only-root probe helper.
  - Added `uacp_sandbox_check` tool handler.
  - Preserved fail-closed standard shell/code behavior.
- `runtime-adapters/hermes/plugins/uacp_guardian/plugin.yaml`
  - Registered `uacp_sandbox_check`.
- `config/guardian-policy.yaml`
  - Added `evidence.containment` classification for `uacp_sandbox_check`.
- `scripts/live_guardian_probe.py`
  - Added positive and negative containment evidence checks.
- `verification/*phase4*`
  - Recorded implementation, live proof, council review, and resolve readiness evidence.
- `outputs/uacp-current-status.yaml` and `outputs/uacp-operational-dashboard.yaml`
  - Synchronized after proof and cleanup verification.

## Containment evidence contract

`uacp_sandbox_check` returns the required evidence shape, including:

- `containment_verified`
- `mechanism`
- resolved workspace and UACP root paths
- path relationship evidence
- bwrap write-probe result
- tool surface/backend distinction
- TTL/evidence reason
- `allow_standard_tool_path: false`

Guardian treats missing, stale, failed, or non-applicable evidence as `filesystem_guard_verified=False`.

## Required probe cases

Final live proof status: pass, 48 checks.

Covered:

- terminal without containment → block
- execute_code without containment → block
- bwrap evidence probe → pass as mechanism evidence
- workspace under UACP_ROOT → block
- execute_code backend unproven → block
- unknown plugin mutator → block
- live symlink bindings → pass
- duplicate local plugin copies absent → pass
- temporary symlink probe absent → pass

Deferred:

- terminal executing through a real contained runtime seam → next phase
- execute_code with verified backend containment → next phase or later

## Rollback

Rollback remains simple because no shell/code allow path was enabled:

- Remove/disable `uacp_sandbox_check` classification or handler if evidence semantics are found unsafe.
- Keep `filesystem_guard_verified=False` for standard tool paths.
- Re-run live proof to confirm shell/code fail-closed.

## Verification before closure

- YAML parse: pass
- Live Guardian proof: pass, 48 checks
- Post-implementation Agent Council: pass
- Heartgate EXECUTE→VERIFY: warn accepted, no blockers
- Heartgate VERIFY→RESOLVE: warn accepted, no blockers

## Final deferred items

- Design and implement a real contained execution seam before any UACP-bound shell/code allow path can be enabled.
- Keep `execute_code` blocked until backend-specific containment evidence exists.
- Re-run live proof and Agent Council before claiming any shell/code allow path is enabled.
