# UACP Phase 4 — Filesystem Containment Plan

Run ID: `uacp-phase4-filesystem-containment-20260513-215531`
Phase: `PLAN`
Status: draft, pre-EXECUTE

## Objective

Enable UACP-bound `exec.shell` and `exec.code_with_tool_proxy` only when the runtime can prove filesystem containment. The default remains fail-closed.

## Authority and boundaries

- Authority: Mike explicitly requested Phase 4 start in the private control session.
- UACP declares required posture and evidence obligations.
- Guardian verifies runtime-provided evidence inside the controlled tool path.
- Host/runtime supplies real containment.
- Manual/operator-side edits remain out-of-band and untrusted until revalidated.
- No upstream Hermes Agent push or PR in this phase.
- No broad shell/code enablement without positive proof.

## Council constraints accepted into PLAN

The focused Agent Council returned `concerns`, not `fail`. The following are hard requirements before EXECUTE can be accepted:

1. Name a concrete containment mechanism.
2. Make `uacp_sandbox_check` or equivalent evidence generation required for allow decisions.
3. Define terminal and `execute_code` separately; block `execute_code` if backend containment cannot be proven.
4. Include symlink-aware path resolution, mount/read-only inspection where applicable, and actual write-probe failure from execution context.
5. Scope allow behavior to standard guarded Hermes tool-call paths; non-standard plugin dispatch/slash/control-plane paths stay out of scope or blocked.
6. Define evidence TTL/invalidation and rollback to fail-closed.
7. Generate PLAN-phase gate selection and Heartgate-check PLAN→EXECUTE transition before implementation.

## Proposed implementation shape

### Target files

- `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py`
  - Add containment verification helper.
  - Add `uacp_sandbox_check` tool handler if implementation proceeds.
  - Ensure `filesystem_guard_verified=True` is set only after positive evidence.
- `runtime-adapters/hermes/plugins/uacp_guardian/plugin.yaml`
  - Register `uacp_sandbox_check` if implemented.
- `runtime-adapters/hermes/plugins/uacp_guardian/kernel.py`
  - No change expected unless PLAN→EXECUTE discovers a missing neutral-kernel concept.
- `config/guardian-policy.yaml`
  - Add explicit classification for `uacp_sandbox_check` if implemented.
- `scripts/live_guardian_probe.py`
  - Add positive/negative containment proof cases.
- `verification/*phase4*`
  - Record evidence artifacts after execution.
- `outputs/uacp-current-status.yaml` and `outputs/uacp-operational-dashboard.yaml`
  - Update only after proof exists.

### Containment evidence contract

`uacp_sandbox_check` or equivalent must return:

- `containment_verified`: boolean
- `mechanism`: one of `filesystem_sandbox`, `readonly_mount_for_protected_paths`, `tool_runtime_write_guard`, or `unverified`
- `workspace_resolved`: resolved workspace path
- `uacp_root_resolved`: resolved UACP root path
- `path_relationship`: whether either path is inside the other
- `mount_evidence`: read-only/mount namespace observations when available
- `write_probe`: attempted write result from the execution context
- `tool_surface`: `exec.shell` or `exec.code_with_tool_proxy`
- `backend`: terminal backend or execute_code backend identifier
- `expires_at` or `ttl_seconds`
- `verdict_reason`

Guardian must treat missing, stale, or failed evidence as `filesystem_guard_verified=False`.

### Required probe cases

- Existing negative: terminal without containment → block.
- Existing negative: execute_code without containment → block.
- New positive candidate: terminal in verified contained workspace → allow_with_audit.
- New negative: terminal with workspace under UACP_ROOT → block.
- New negative: terminal where write probe to UACP_ROOT succeeds → block.
- New positive candidate: execute_code with verified backend containment → allow_with_audit.
- New negative: execute_code backend unknown/shared host filesystem without proof → block.

If no positive containment mechanism can be safely proven locally, Phase 4 should resolve as design-only with fail-closed preserved.

## Rollback

Rollback trigger:

- Any containment probe fails after an allow path was added.
- `uacp_sandbox_check` evidence is stale/malformed.
- Live proof shows shell/code can write to UACP_ROOT when it should not.

Rollback action:

- Revert adapter changes or disable allow path by policy/config.
- Force `filesystem_guard_verified=False` for affected tool surface.
- Re-run live proof to confirm shell/code fail-closed.
- Record rollback verification artifact before updating status.

## Verification before EXECUTE may close

- YAML validates.
- Python compiles for touched adapter/probe files.
- Live Guardian proof passes all Phase 4 cases.
- Verification artifact records command, result, and residual risks.
- Agent Council review runs after implementation if behavior changes execution permission.

## Transition gates

- Before EXECUTE: create PLAN-phase gate-selection artifact and PLAN→EXECUTE transition artifact; run `uacp_heartgate_check`.
- Before VERIFY→RESOLVE: run proof harness, council review, and Heartgate on transition artifact.
