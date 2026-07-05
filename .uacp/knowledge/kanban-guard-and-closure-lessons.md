---
type: analysis
id: kanban-guard-and-closure-lessons
title: Kanban Guard and Closure Lessons
description: 7-step closure evidence pattern, workspace-separation boundary, completion metadata field list, completion_blocked_uacp_metadata event, 5-case verification shape, and non-goals for Kanban guard phases.
tags: [kanban, closure, evidence, coordination]
timestamp: 2026-06-17
---

# Kanban Guard and Closure Lessons

Durable lessons for UACP-bound Kanban completion guard semantics, phase closure evidence patterns, and the workspace-separation boundary. Drawn from Phase 4B resolve lessons and Phase 5 Kanban guard work (2026-05-14).

---

## Core Principle: Kanban Is Coordination Memory, Not Lifecycle State

Kanban records durable tasks, dependencies, status, and handoffs. It is not a UACP phase state machine. A Kanban `done` status is not a UACP phase transition. UACP phase state remains in `state/current.yaml` and run manifests.

Existing UACP Kanban protection may cover task creation and dispatch without protecting the completion edge. For UACP-bound tasks, **completion itself is a governance event**.

---

## 7-Step Closure Evidence Pattern

For runtime phase closure and verify-to-resolve transitions:

1. Create `verify-to-resolve` transition artifact with full schema fields.
2. Run `uacp_heartgate_check` before updating run/current state.
3. If Heartgate blocks on status vocabulary, rewrite to canonical `pass` + warnings/deferred items, not looser status strings like `pass_with_concerns`.
4. Update run manifest to `phase: resolve` and a precise resolved status.
5. Update `state/current.yaml`.
6. Write a resolution artifact under `verification/` with six sections:
   - closure evidence
   - resolved invariants
   - repository hygiene
   - rollback
   - carried-forward hardening
   - side effects performed/not performed
7. Re-run the live proof harness after state closure when the phase changed runtime behavior.

---

## Workspace-Separation Boundary

`uacp_contained_shell` needs a **separate workspace that is not `UACP_ROOT`**. Invoking it with `workspace` set to a path inside `UACP_ROOT` (or where `UACP_ROOT` is inside the workspace) correctly fails containment verification.

For UACP-root writes, use governed writers — not contained shell.

---

## Do Not Encode Transient Failure as "Contained Shell Broken"

If a specific contained-shell invocation fails because the workspace was wrong, the durable lesson is the boundary rule, not that `uacp_contained_shell` is non-functional. Record the specific failure as a boundary-enforcement proof and carry forward the correct workspace-separation requirement.

---

## Heartgate Enum Discipline

Heartgate transition artifacts reject non-canonical status/state values such as `pass_with_concerns` inside `invariant_summary[].status` or `cluster_summary[].state`. Preferred shape:

- Set invariant/cluster status to `pass` when the phase can close.
- Carry the concern text in `warnings` and `deferred_items` with owner, residual risk, `accepted_by`, and a concrete condition.
- Keep `blockers: []` only when the concern is genuinely non-blocking.

This preserves strict transition validation while avoiding the false implication that council concerns were ignored.

---

## Completion Metadata Field List

For UACP-bound task completion, require all of the following fields:

| Field | Requirement |
|---|---|
| `uacp_run_id` | Must match stored governance context |
| `uacp_phase` | Must match stored governance context |
| `authority_artifact` | Must be present |
| `guardian_policy_version` | Must match stored governance context |
| `declared_side_effects` | Must be present |
| `evidence_refs` | Must be non-empty string or list |

The payload may be accepted as top-level metadata or nested under `uacp_completion`/`uacp`, but the semantic fields must be present. Mismatch on run id, phase, or Guardian policy version should block completion before task state changes.

---

## Completion Validation Logic

1. Add an explicit `_UACP_COMPLETION_REQUIRED` field list near the existing UACP context schema.
2. Add a helper that extracts completion metadata from either top-level metadata or nested `uacp_completion` / `uacp`.
3. Add a helper that validates: required fields are present, `evidence_refs` is non-empty, stored governance context exists, run id / phase / policy version match stored context.
4. In `complete_task()`, run the validation before any `tasks.status = 'done'` mutation.
5. On rejected completion, append an auditable event: **`completion_blocked_uacp_metadata`**, then raise/return an error without changing task state.
6. On accepted completion, include a compact `uacp_completion` summary in the completed event payload.
7. Update model tool and CLI help text so workers know UACP-bound completion requires metadata/evidence.

---

## Non-Goals

- Do **not** require UACP completion metadata for ordinary non-governed Kanban tasks.
- Do **not** treat a Kanban task status as UACP lifecycle state.
- Do **not** make Kanban the UACP phase state machine.
- Do **not** alter ordinary non-UACP completion behavior.
- Do **not** weaken Guardian/Heartgate.
- Do **not** push public Hermes upstream without explicit approval.

---

## 5-Case Verification Shape

Targeted tests for Kanban guard work:

| Case | Expected Outcome |
|---|---|
| Positive: UACP-bound completion with complete valid metadata | Completion succeeds |
| Negative: UACP-bound completion missing evidence | Blocked; task remains non-terminal |
| Negative: UACP-bound completion with mismatched run/phase/authority/policy metadata | Blocked |
| Regression: non-UACP completion | Succeeds unchanged |
| Traceability: completed UACP-bound task | Links to active run and evidence artifact |

---

## Low-Confidence-Delegate Pitfall

Do not trust council self-reports blindly about missing files. Verify whether the delegate actually read the requested files before treating findings as blockers. If a council role reports missing artifacts that the main session has verified, record it as low-confidence rather than as a true blocker.

---

## PROPOSE Non-Goals for Kanban Guard Phases

Include these explicitly in the proposal to constrain scope:

- Do not make Kanban the UACP phase state machine.
- Do not alter ordinary non-UACP completion behavior.
- Do not weaken Guardian/Heartgate.
- Do not push public upstream without explicit approval.

---

## Hardening Items to Carry Forward

After Phase 4B/5 type closures:

- Bounded stdout/stderr capture for contained shell.
- Host read exposure threat model and possible narrower bind mounts.
- Attestation lifecycle cleanup/persistence only if restart continuity becomes necessary.

---

> _Sources: `skills/references/phase4b-resolve-lessons-20260514.md`, `skills/references/phase5-kanban-completion-guard-20260514.md`, and `skills/references/phase5-kanban-guard-start-pattern-20260514.md`. All removed in ADR-0017 / Step 2 Slice 3. Hermes-internal file paths (kanban_db.py, kanban_tools.py, etc.) and stale dashboard refs dropped._
