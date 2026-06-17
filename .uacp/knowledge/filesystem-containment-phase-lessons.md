---
type: lessons
title: Filesystem Containment Phase Lessons
description: Evidence-vs-execution distinction, boundary-correction principle, bwrap design, write-probe requirement, Heartgate YAML shape, and 10-step phase-start sequence for filesystem containment phases.
tags: [filesystem, containment, security, heartgate]
timestamp: 2026-06-17
---

# Filesystem Containment Phase Lessons

Durable lessons for UACP-bound filesystem containment design, contained shell execution seams, and security-sensitive runtime phases. Anchored by the 2026-05-14 containment seam notes and the 2026-05-13 phase-start pattern.

---

## Core Distinction: Evidence vs. Execution

| Surface | Role |
|---|---|
| `uacp_sandbox_check` | Evidence-only — returns containment status for VERIFY artifacts; does not grant execution authority. |
| `uacp_contained_shell` | Governed execution surface — actual UACP-bound shell/code runner. |

Standard `terminal` / `execute_code` stay fail-closed unless backend-specific containment is proven for those surfaces. The implementation uses bubblewrap (`bwrap`) with:

- `--ro-bind /` — read-only host root bind (deliberate read-exposure tradeoff, not equivalent to full host isolation)
- writable sandbox workspace bind — a separate workspace directory distinct from `UACP_ROOT`

---

## The Boundary Correction Principle (Verbatim)

> **Containment is a host/runtime property. UACP declares the required posture; Guardian verifies runtime-provided evidence; the host/runtime supplies the actual isolation. If that evidence is absent, protected shell/code remains fail-closed.**

Corollary: do not frame containment as UACP preventing every possible user-side mutation. Manual edits in VS Code, direct config changes, symlink replacement, and external runtimes without UACP integration are outside the governed runtime boundary. They are treated as out-of-band changes requiring revalidation before trust.

---

## Practical Guardrails

- Keep the shell seam separate from the evidence checker; do not let the checker self-attest standard tool paths.
- Run a **write probe** against `UACP_ROOT` before every command execution and require it to confirm writes are blocked.
- The contained shell returns a **short-lived attestation record** and rejects stale attestation reuse.
- Treat `--ro-bind /` as a deliberate read-exposure tradeoff, not as equivalent to full host isolation.
- Keep output capture bounded if commands can emit large stdout/stderr streams.
- Treat in-memory attestation stores as process-local unless a durable store is intentionally added later.
- If a transition artifact uses Heartgate, ensure the transition file includes the full schema fields expected by the kernel; warnings must be explicitly owned.

---

## Workspace Separation Boundary

`uacp_contained_shell` needs a **separate workspace** — not `UACP_ROOT`. Invoking it with `workspace=/home/norty/.hermes/uacp` correctly fails containment verification because the execution workspace is under (or overlaps) `UACP_ROOT`.

For UACP-root writes, continue using governed writers:

- `uacp_state_write` for `state/`
- `uacp_artifact_write` for verification/output artifacts
- `uacp_doc_write` for canonical docs
- `uacp_config_write` for config

Use `uacp_contained_shell` for contained execution in a separate workspace that can be made writable while `UACP_ROOT` remains read-only.

---

## Risk Table and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Symlink traversal bypasses containment | Low | High | Use `Path.resolve()` and check against `UACP_ROOT` |
| Hermes sandbox backend changes | Medium | Medium | Pin containment check to sandbox working directory; add live probe test |
| Operator runs shell without containment | Low | High | Keep `fail_closed_if_unavailable: true`; require explicit `filesystem_guard_verified=True` |
| Nested mounts not read-only | Low | Medium | Check `statvfs ST_RDONLY` on `UACP_ROOT` and all parent mounts |

---

## Breakglass Rules

- Breakglass records must include `affected_scope` and `expiry`.
- Global-disable of containment is **blocked**.
- Breakglass is not a substitute for fixing the containment gap.

---

## 10-Step Phase-Start Sequencing

When starting a security-sensitive UACP runtime containment phase:

1. Load UACP lifecycle skills and rehydrate current state from artifacts, not chat memory alone.
2. Create a TRIAGE artifact under `state/runs/` before writing a proposal.
3. Create a bounded PROPOSE artifact and a PROPOSE gate-selection artifact.
4. Run a focused tier-2 Agent Council before implementation with role-diverse review: Security/Guardian reviewer, Runtime/filesystem isolation reviewer, Lifecycle/verification reviewer.
5. Record a formal council synthesis artifact under `verification/`.
6. Write a propose → plan transition artifact and run `uacp_heartgate_check` before accepting PLAN.
7. If Heartgate blocks on warnings/deferred items, rewrite the transition so that:
   - `warnings` are structured maps with `owner` and `residual_risk`.
   - warned cluster artifact paths appear in `accepted_exceptions` with `artifact_path`, `rationale`, and `owner`.
   - each `deferred_items` entry has `cluster_id`, `owner`, `condition`, and `accepted_by`.
8. Create the PLAN artifact and PLAN gate-selection artifact only after the transition is accepted/pass-or-warn.
9. Update `state/current.yaml` through `uacp_state_write` after the Heartgate-checked transition.
10. Commit the UACP artifact checkpoint locally before implementation.

---

## Heartgate YAML Shape (Containment Transition)

Minimal shape when warnings or deferred items are present:

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

Heartgate treats free-text warnings and incomplete deferred items as blockers. Use structured records, not prose lists.

---

## 7 Pre-EXECUTE Council Constraints

The following concerns must be resolved or explicitly deferred before EXECUTE begins:

1. A concrete containment mechanism is named, not just "sandbox" or "read-only check".
2. `filesystem_guard_verified` is never self-attested by prompt/context alone.
3. `uacp_sandbox_check` or equivalent evidence is required for any allow decision.
4. Terminal and `execute_code` have separate backend-specific containment proofs.
5. Verification includes symlink-aware path checks, mount/read-only inspection where applicable, and a real write probe from the execution context.
6. Non-standard plugin dispatch, slash commands, and control-plane paths are explicitly out of scope or blocked.
7. Evidence has TTL/invalidation rules and rollback forces fail-closed.

---

## Verification Signals That Matter

- Live probe shows the contained shell can execute and the write probe blocks `UACP_ROOT`.
- Standard shell/code paths remain blocked without containment evidence.
- Stale attestation reuse fails.
- The verification artifact points at durable probe evidence under `verification/`.

---

## Do Not Persist as Doctrine

Do not encode the transient failure of a particular command invocation as "contained shell does not work." The durable rule is the boundary: contained shell needs a separate workspace and should not be used as the writer path for `UACP_ROOT` mutation.

---

> _Sources: `skills/references/contained-shell-execution-seam-20260514.md` (anchor — preserved in full), `skills/references/containment-design-direction-20260514.md`, and `skills/references/phase4-filesystem-containment-start-pattern-20260513.md`. All removed in ADR-0017 / Step 2 Slice 3. Stale open-blockers dashboard narrative and completed design-review tasks dropped._
