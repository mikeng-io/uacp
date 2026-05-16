# UACP Skill Enforcement Spec

This is the authoritative authority record for what each UACP skill is allowed to do at runtime. It is the **source of truth** that the per-skill `SKILL.md` YAML frontmatter mirrors and that the kernel reads via `config/phase-transitions.yaml`. When the spec and the mirror disagree, this spec and the canonical config win.

## Authority chain

```
docs/reference/skill-enforcement-spec.md (intent)
    │
    └─→ config/phase-transitions.yaml stages.<phase>.allowed_tools / forbidden_tools / phase_exit_invariants
            │
            └─→ skills/devops/uacp/uacp-<phase>/SKILL.md (mirror; config wins on conflict)
```

The kernel reads phase admissibility (Layer B) from `config/phase-transitions.yaml`. The skill SKILL.md files are mirrors for self-documentation and editor discoverability.

## Per-skill contract

For each skill, this section lists: phase, Guardian tools allowed, Guardian tools forbidden, write surfaces (declared via the allowed tools' Layer A capabilities), and PIV obligation.

### `uacp-triage` (phase: triage)

**Purpose**: admission control, scope/granularity calibration, governance routing.

**Allowed tools**: `uacp_artifact_write`, `uacp_state_write`, `uacp_gate_ledger_append`, `uacp_heartgate_check`, `uacp_doc_write`, `uacp_config_write`, `uacp_escalation_event`.

**Forbidden tools**: `terminal`, `execute_code`.

**Write surfaces (Layer A)**: `state/`, `plans/`, `proposals/`, `executions/`, `verification/`, `outputs/`, `knowledge/`, `docs/`, `config/`. (Triage is permitted to update governance docs/configs.)

**PIV obligation**: run PIV at end of TRIAGE; append `gate: PIV, phase: triage, result: pass|fail` to the gate ledger.

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

**Write surfaces**: `outputs/`, `knowledge/`, `state/`, plus other artifact roots.

**PIV obligation**: required.

**Phase exit invariants**: `outputs/{run_id}*`, ledger entry `VERIFY->RESOLVE`.

**Phase 2 obligation**: emit `outputs/{run_id}-lessons.yaml` matching `config/artifact-schemas.yaml#lessons`, including `ledger_citations` for non-trivial lessons.

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
| Phase admissibility (Layer B) | `Guardian._phase_layer_check` reads `config/phase-transitions.yaml stages.<phase>.allowed_tools/forbidden_tools` |
| Per-category writer (Layer A) | `Guardian.evaluate()` reads `config/guardian-policy.yaml protected_categories.<cat>.allowed_tools` |
| Self-attesting containment | `Guardian._filesystem_guard_verified` reads `config/guardian-policy.yaml self_attesting_tools.names` |
| Phase exit invariants | `Heartgate._validate_phase_exit_invariants` reads `stages.<phase>.phase_exit_invariants` |
| PIV obligation | `Heartgate._validate_piv_record` reads `piv_rule` + run gate-ledger; enforces per-check pass evidence (each piv_id ∈ {piv_1..piv_5} carrying explicit `result: pass` either as a mapping entry in `checks[]` or via sibling `check_results: {piv_id: pass}`) — Global review SKEP-G-002 generalized the Phase 3 R1 PLAN_VALIDATION pattern to PIV |
| Plan validation | `Heartgate._validate_plan_validation_gate` reads `plan_validation_gate` (incl. `ledger_required_fields`, `ledger_required_phase`, declared `checks`) + run gate-ledger; enforces per-check pass evidence (Phase 3 R1/R2) |
| Run registry | `Heartgate._validate_run_registry_overlap` reads `run_registry_rule` + `state/run-registry.yaml`; uses `_canon_write_path`/`_paths_overlap` (PurePosixPath segment match, Phase 3 R1) |
| Run registry mutation | `uacp_run_registry_update` enforces caller-binding + write-path canonicalization; `uacp_state_write` refuses direct writes to `state/run-registry.yaml` (Phase 3 R1/R2) |
| Scope handler refusals | `Heartgate._validate_scope_artifact` reads `cross_checks.scope_write_paths_vs_layer_b.handler_refusals` so a scope cannot launder paths the handler refuses (Phase 3 R1) |
| Escape-hatch shape | `Heartgate._validate_evidence_dispositions` validates that `handled_findings_chain` / `accepted_exceptions` entries are non-empty mappings with required fields, not garbage placeholders (Phase 3 R2 SKEP-R1-002) |
| Escalation events (Phase 4.4 stub) | `_handle_uacp_escalation_event` enforces UACP context, severity/mode enums, required `mode` field, PIPE_BUF size bound, escalation-dir containment check, embedded-newline refusal; writes to `state/escalations/{run_id}.jsonl`. Operator-polling only — push-notify is Phase 5. Trigger-ID validation against `config/autonomy-policy.yaml#escalation_triggers.triggers` is deferred to Phase 5 (no kernel reader yet). |
| Operating mode (Phase 4.1 stub) | `state/current.yaml#uacp_mode` declared with default=manual. **No kernel reader in Phase 4** — `enforcement_status: stub_only_phase_4`. Skills consult `config/autonomy-policy.yaml` as guidance. Phase 5 adds the first reader. |
| Scope write_paths | `Heartgate._validate_scope_artifact` reads `config/artifact-schemas.yaml#scope` + `plans/{run_id}-scope.yaml` |

If a skill SKILL.md mirror drifts from this spec or from `config/phase-transitions.yaml`, the canonical config wins. Drift is recoverable through normal commits — there is no audit harness yet (deferred for Phase 4 autonomous-mode verification cycles).
