---
type: reference
title: UACP Skill Enforcement Spec
description: Authoritative per-skill authority record listing allowed tools, forbidden tools, write surfaces, and PIV obligations enforced by the kernel.
tags: [skill, enforcement, guardian, authority]
timestamp: 2026-06-18
---

# UACP Skill Enforcement Spec

This is the authoritative authority record for what each UACP skill is allowed to do at runtime. It is the **source of truth** that the per-skill `SKILL.md` YAML frontmatter mirrors and that the kernel enforces from the codified stages grammar in `engines/domain/phase_transitions.py` (`stages_default()`; `load_phase_transitions` injects it as the effective `stages` since `config/phase-transitions.yaml` no longer carries a `stages` block — slimmed Slice 4b). When the spec and the mirror disagree, this spec and the codified grammar win.

## Authority chain (local precedence — scoped)

> **Scope:** this is a LOCAL artifact-precedence order for the phase-stage grammar only —
> which artifact wins when the spec, the codified stages, and a SKILL.md mirror disagree. It
> sits INSIDE the single canonical authority chain (the priority table in `AGENTS.md`; see the
> 2026-07-17 decision-log entry) and is consistent with it: intent docs above code, code above
> skill mirrors. It is not a second system-wide chain.

```
docs/reference/skill-enforcement-spec.md (intent)
    │
    └─→ engines/domain/phase_transitions.py stages_default(): stages.<phase>.allowed_tools / forbidden_tools / phase_exit_invariants
            │   (injected by load_phase_transitions as the effective stages; config/phase-transitions.yaml carries no stages block)
            │
            └─→ skills/devops/uacp/uacp-<phase>/SKILL.md (mirror; codified grammar wins on conflict)
```

The kernel reads phase admissibility (Layer B) from the codified `stages_default()` in `engines/domain/phase_transitions.py` (injected as the effective `stages` by `load_phase_transitions`). The skill SKILL.md files are mirrors for self-documentation and editor discoverability.

## Per-skill contract

For each skill, this section lists: phase, Guardian tools allowed, Guardian tools forbidden, write surfaces (declared via the allowed tools' Layer A capabilities), and PIV obligation.

### `uacp-triage` (phase: triage)

**Purpose**: admission control, scope/granularity calibration, governance routing.

**Allowed tools**: `uacp_artifact_write`, `uacp_state_write`, `uacp_gate_ledger_append`, `uacp_heartgate_check`, `uacp_doc_write`, `uacp_config_write`, `uacp_escalation_event`.

**Forbidden tools**: `terminal`, `execute_code`.

**Write surfaces (Layer A)**: `state/`, `plans/`, `proposals/`, `executions/`, `verification/`, `.outputs/`, `knowledge/`, `docs/`, `config/`. (Triage is permitted to update governance docs/configs.)

**PPV obligation**: run the post-phase verification (PPV) self-eval at end of TRIAGE; append `gate: PPV, phase: triage, result: pass|fail` to the gate ledger. (PPV is the legacy end-of-phase ledger rule, formerly recorded as `gate: PIV`; distinct from Phase Intent Verification.)

**Phase exit invariants**: `proposals/{run_id}-triage*.yaml`, ledger entry `TRIAGE_COMPLETE`.

### `uacp-propose` (phase: propose)

**Purpose**: formalize authority, side effects, viability, proposal artifact.

**Allowed tools**: `uacp_artifact_write`, `uacp_state_write`, `uacp_gate_ledger_append`, `uacp_heartgate_check`, `uacp_doc_write`, `uacp_escalation_event`.

**Forbidden tools**: `terminal`, `execute_code`.

**Write surfaces**: `proposals/`, `state/`, `docs/`, plus other artifact roots via `uacp_artifact_write`.

**PIV obligation**: required.

**Phase exit invariants**: `proposals/{run_id}*.yaml`, ledger entry `TRIAGE->PROPOSE`.

### `uacp-plan` (phase: plan)

**Purpose**: convert proposal into bounded plan + scope artifact.

**Allowed tools**: `uacp_artifact_write`, `uacp_state_write`, `uacp_gate_ledger_append`, `uacp_heartgate_check`, `uacp_escalation_event`.

**Forbidden tools**: `terminal`, `execute_code`.

**Write surfaces**: `plans/`, `state/`, plus other artifact roots.

**PIV obligation**: required.

**Phase exit invariants**: `plans/{run_id}*`, ledger entry `PROPOSE->PLAN`.

**Phase 3.1 obligation**: emit a `PLAN_VALIDATION` ledger entry with `result: pass` before PLAN→EXECUTE is requested.

### `uacp-execute` (phase: execute)

**Purpose**: perform bounded implementation through the approved plan.

**Allowed tools**: `uacp_doc_write`, `uacp_config_write`, `uacp_state_write`, `uacp_artifact_write`, `uacp_gate_ledger_append`, `uacp_contained_shell`, `uacp_sandbox_check`, `uacp_heartgate_check`, `terminal`, `execute_code`, `uacp_escalation_event`.

**Forbidden tools**: (none — full shell/exec available, but governed by scope.write_paths Layer A cross-check).

**Write surfaces**: per the active run's `plans/{run_id}-scope.yaml#write_paths` — Heartgate enforces. Shell/exec target the workspace (declared outside UACP_ROOT) and do NOT satisfy UACP-rooted scope.write_paths; they are governed by `uacp_contained_shell`'s bwrap attestation.

**PIV obligation**: required. EXECUTE-local council is required for non-trivial implementation work.

**Phase exit invariants**: `executions/{run_id}*`, ledger entry `PLAN->EXECUTE`.

### `uacp-verify` (phase: verify)

**Purpose**: validate completed work against evidence clusters; emit disposition pairs.

**Allowed tools**: `uacp_artifact_write`, `uacp_state_write`, `uacp_gate_ledger_append`, `uacp_heartgate_check`, `uacp_sandbox_check`, `uacp_contained_shell`, `uacp_escalation_event`.

**Forbidden tools**: `terminal`, `execute_code` (use `uacp_contained_shell` for any shell needs).

**Write surfaces**: `verification/`, `state/`, plus other artifact roots.

**PIV obligation**: required.

**Phase exit invariants**: `verification/{run_id}*`, ledger entry `EXECUTE->VERIFY`.

**Phase 2 obligation**: for each non-deferred, non-not_applicable cluster, produce a verified-facts + assumptions pair under `verification/{run_id}-{cluster}-*.md`.

### `uacp-resolve` (phase: resolve)

**Purpose**: finalize outputs, emit structured lessons, archive.

**Allowed tools**: `uacp_artifact_write`, `uacp_state_write`, `uacp_gate_ledger_append`, `uacp_heartgate_check`, `uacp_escalation_event`.

**Forbidden tools**: `terminal`, `execute_code`.

**Write surfaces**: `.outputs/`, `knowledge/`, `state/`, plus other artifact roots.

**PIV obligation**: required.

**Phase exit invariants**: `.outputs/{run_id}*`, ledger entry `VERIFY->RESOLVED`.

**Phase 2 obligation**: emit `.outputs/{run_id}-lessons.yaml` matching the `lessons` schema in `engines/domain/artifact_schema.py` (`artifact_schemas_dict()`; `config/artifact-schemas.yaml` deleted Slice 5), including `ledger_citations` for non-trivial lessons.

### `uacp-state` (cross-phase)

**Purpose**: exclusive mutator of `state/`.

**Allowed tools**: `uacp_state_write`, `uacp_gate_ledger_append`, `uacp_run_registry_update`, `uacp_escalation_event`.

**Forbidden tools**: `terminal`, `execute_code`.

**Write surfaces**: `state/` (per the governed writer's Layer A). Two sub-paths are protected from `uacp_state_write` and routed through narrow writers:
- `state/gate-ledger/{run_id}.jsonl` — `uacp_gate_ledger_append` only.
- `state/run-registry.yaml` — `uacp_run_registry_update` only (Phase 3.2 / R1).

uacp-state has no Layer B entry of its own (it's `phase: '*'` / cross-phase); admissibility comes from the active phase's `allowed_tools`. Path exclusivity for both sub-paths is enforced inside the writer handlers (see `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py`).

**PIV obligation**: cross-phase; no own PIV. Invoked from whichever phase needs state mutation.

**Critical rule**: `state/run-registry.yaml` is mutated only through `uacp_run_registry_update`, which mechanically enforces caller-binding (`entry.run_id == caller.uacp_run_id`) and write-path canonicalization (rejects `..`, absolute paths, wildcards). Direct `uacp_state_write` calls to this path are refused.

## Mechanical enforcement

| Authority | Where enforced |
|---|---|
| Phase admissibility (Layer B) | `Guardian._phase_layer_check` reads the effective `stages.<phase>.allowed_tools/forbidden_tools` — the codified `stages_default()` in `engines/domain/phase_transitions.py`, injected by `load_phase_transitions` (no `stages` block in `config/phase-transitions.yaml`) |
| Per-category writer (Layer A) | `Guardian.evaluate()` reads `config/uacp.toml [guardian] protected_categories.<cat>.allowed_tools` |
| Self-attesting containment | `Guardian._filesystem_guard_verified` reads `config/uacp.toml [guardian] self_attesting_tools.names` |
| Phase exit invariants | `Heartgate._validate_phase_exit_invariants` reads `stages.<phase>.phase_exit_invariants` |
| PPV obligation (legacy post-phase verification ledger rule; formerly "PIV") | `Heartgate._validate_ppv_record` reads `ppv_rule` + run gate-ledger; enforces per-check pass evidence (each ppv_id ∈ {ppv_1..ppv_5} carrying explicit `result: pass` either as a mapping entry in `checks[]` or via sibling `check_results: {ppv_id: pass}`) — Global review SKEP-G-002 generalized the Phase 3 R1 PLAN_VALIDATION pattern to PPV |
| Plan validation | `Heartgate._validate_plan_validation_gate` reads `plan_validation_gate` (incl. `ledger_required_fields`, `ledger_required_phase`, declared `checks`) + run gate-ledger; enforces per-check pass evidence (Phase 3 R1/R2) |
| Run registry | `Heartgate._validate_run_registry_overlap` reads `run_registry_rule` + `state/run-registry.yaml`; uses `_canon_write_path`/`_paths_overlap` (PurePosixPath segment match, Phase 3 R1) |
| Run registry mutation | `uacp_run_registry_update` enforces caller-binding + write-path canonicalization; `uacp_state_write` refuses direct writes to `state/run-registry.yaml` (Phase 3 R1/R2) |
| Scope handler refusals | `Heartgate._validate_scope_artifact` reads `cross_checks.scope_write_paths_vs_layer_b.handler_refusals` so a scope cannot launder paths the handler refuses (Phase 3 R1) |
| Escape-hatch shape | `Heartgate._validate_evidence_dispositions` validates that `handled_findings_chain` / `accepted_exceptions` entries are non-empty mappings with required fields, not garbage placeholders (Phase 3 R2 SKEP-R1-002) |
| Escalation events (Phase 4.4 stub) | `_handle_uacp_escalation_event` enforces UACP context, severity/mode enums, required `mode` field, PIPE_BUF size bound, escalation-dir containment check, embedded-newline refusal; writes to `state/escalations/{run_id}.jsonl`. Operator-polling only — push-notify is Phase 5. Trigger-ID validation against `config/uacp.toml [autonomy.escalation_triggers]` triggers is deferred to Phase 5 (no kernel reader yet). |
| Operating mode (Phase 4.1 stub) | `state/current.yaml#uacp_mode` declared with default=manual. **No kernel reader in Phase 4** — `enforcement_status: stub_only_phase_4`. Skills consult `config/uacp.toml [autonomy]` as guidance. Phase 5 adds the first reader. |
| Scope write_paths | `Heartgate._validate_scope_artifact` reads `engines/domain/artifact_schema.py` (`artifact_schemas_dict()` key `scope`; `config/artifact-schemas.yaml` deleted Slice 5) + `plans/{run_id}-scope.yaml` |

If a skill SKILL.md mirror drifts from this spec or from the codified stages grammar (`engines/domain/phase_transitions.py` `stages_default()`), the codified grammar wins. Drift is recoverable through normal commits — there is no audit harness yet (deferred for Phase 4 autonomous-mode verification cycles).
