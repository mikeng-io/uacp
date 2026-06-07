# Phase 4B — Contained Runtime Execution Seam Plan

Run ID: `uacp-phase4b-contained-execution-seam-20260514-082154`
Phase: `PLAN`
Status: draft, pre-EXECUTE

## Objective

Create a real contained shell execution seam for UACP-bound shell commands. The seam must execute inside verified bwrap read-only-root containment and preserve fail-closed behavior for standard Hermes terminal and `execute_code` paths until the new seam is proven.

## Chosen containment mechanism

Implement a new UACP-owned Hermes Guardian tool surface named `uacp_contained_shell` inside `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py`.

The tool will:
- accept a bounded shell command plus an explicit workspace,
- resolve workspace and UACP root paths with symlink-aware checks,
- launch the command via `bwrap --ro-bind / /` with a writable workspace mount,
- prevent writes to `UACP_ROOT`,
- return execution evidence and a short-lived attestation record,
- mark containment stale on TTL expiry or policy/runtime drift.

This is a new execution seam, not a reclassification of the existing evidence-only `uacp_sandbox_check`.

## Authority and boundaries

- Authority: Mike explicitly requested continuation after Phase 4 completion checks passed.
- UACP declares required posture and evidence obligations.
- Guardian verifies runtime-provided evidence and short-lived attestation.
- Host/runtime supplies real containment through the new tool surface.
- Manual/operator-side edits remain out-of-band and untrusted until revalidated.
- No upstream Hermes Agent push or PR in this phase.
- No broad standard terminal allow path without the contained seam.
- `execute_code` backend containment remains deferred until the shell seam is proven.

## PLAN requirements accepted from Council

The proposal-review council passed with plan-scoped concerns. The plan must now resolve them:

1. Name the concrete wrapper/integration point.
2. Define how evidence flows from the seam to Guardian.
3. Define TTL/revalidation and rollback to fail-closed.
4. Keep `uacp_sandbox_check` evidence-only.
5. Prove actual execution inside containment, not just a separate write probe.

## Reference status and traceability

- Phase 4 resolution artifact: `.outputs/uacp-phase4-resolution-20260514.yaml`
- Phase 4 resolution run: `uacp-phase4-filesystem-containment-20260513-215531`
- Proposal council artifact: `verification/uacp-phase4b-contained-execution-seam-proposal-council-synthesis-20260514.yaml`

## Proposed implementation shape

### Target files

- `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py`
  - Add `uacp_contained_shell` tool handler.
  - Add attestation/TTL helpers and rollback-to-fail-closed logic.
  - Keep `uacp_sandbox_check` as evidence-only.
- `runtime-adapters/hermes/plugins/uacp_guardian/plugin.yaml`
  - Register `uacp_contained_shell`.
- `config/guardian-policy.yaml`
  - Add `exec.shell.contained` or equivalent category for the new tool.
  - Add evidence TTL and invalidation rules for the contained seam.
- `scripts/live_guardian_probe.py`
  - Add positive/negative contained-shell proof cases.
  - Add stale-attestation and rollback verification.
- `verification/*phase4b*`
  - Record implementation, live proof, council review, and resolution artifacts.
- `.outputs/uacp-current-status.yaml` and `.outputs/uacp-operational-dashboard.yaml`
  - Update only after proof exists.

### Containment evidence contract

The new `uacp_contained_shell` tool must return:

- `containment_verified`: boolean
- `mechanism`: `bwrap_readonly_root`
- `workspace_resolved`
- `uacp_root_resolved`
- `path_relationship`
- `command`
- `exit_code`
- `stdout_tail`
- `stderr_tail`
- `write_probe_blocked`
- `attestation_id`
- `expires_at` or `ttl_seconds`
- `policy_version`
- `verdict_reason`

Guardian must treat missing, expired, or mismatched attestation as `filesystem_guard_verified=False`.

### TTL / invalidation rules

Attestation should become stale when any of the following changes:

- TTL expires.
- Guardian policy version changes.
- bwrap or host containment environment changes.
- workspace path relationship changes.
- execution surface changes from the approved contained tool to any standard Hermes terminal/execute_code path.

Rollback to fail-closed:

- invalidate attestation,
- force `filesystem_guard_verified=False`,
- block the seam until revalidated,
- re-run live proof before any allow path remains enabled.

### Required probe cases

- terminal via `uacp_contained_shell` inside verified containment → allow_with_audit
- terminal via `uacp_contained_shell` with workspace under UACP_ROOT → block
- terminal via `uacp_contained_shell` with stale attestation → block
- terminal via `uacp_contained_shell` with write attempt to UACP_ROOT → block
- standard Hermes terminal outside the new seam → block
- `execute_code` remains blocked because backend containment is not yet proven

## Rollback

Rollback trigger:

- containment probe fails after allow path is added,
- attestation expires or mismatches,
- command execution can write to UACP_ROOT,
- standard Hermes terminal starts behaving as contained without the explicit new tool surface.

Rollback action:

- disable the contained shell allow path,
- invalidate attestation,
- force `filesystem_guard_verified=False`,
- re-run live proof,
- record rollback verification artifact before updating status.

## Verification before EXECUTE may close

- YAML validates.
- Python compiles for touched adapter/probe files.
- Live Guardian proof passes all contained-shell cases.
- Verification artifact records command, result, attestation semantics, and residual risks.
- Agent Council review runs after implementation if behavior changes execution permission.

## Transition gates

- Before EXECUTE: create PLAN→EXECUTE transition artifact and run `uacp_heartgate_check`.
- Before VERIFY→RESOLVE: run proof harness, council review, and Heartgate on transition artifact.
