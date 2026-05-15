# Phase 3 — Governance Completeness

**Phase**: 3 of 4 (Phases 0–4 scheduled)
**Granularity**: 6
**Plugin-only**: yes (no Hermes core changes)
**Prerequisite**: Phase 2 Codex gate passed; drift-reconciliation step completed
**Commit boundary**: one atomic commit after Codex gate passes

## Drift Reconciliation (First Step)

Read `verification/uacp-patch-plan-phase2-codex-review.yaml` before starting any work.
Classify all findings. Pay particular attention to any vocabulary reconciliation between
the scope artifact's blast-radius levels and the triage granularity scale — the plan
validation gate (3.1) and run registry (3.2) must use the same taxonomy.

## Item 3.1 — Plan Validation Gate

**Purpose**: A mandatory structural pre-check that runs before any EXECUTE work begins.
Not a council — a deterministic verification. Recorded in the gate ledger as `PLAN_VALIDATION`.

**Checklist** (all items must pass before EXECUTE starts):
1. `plans/{run_id}-scope.yaml` exists and parses as valid YAML with all required fields.
2. All tools listed in the plan's `allowed_tools` are registered in Guardian's tool registry.
3. The scope artifact's `write_paths` are a subset of the proposal's declared `side_effects.paths`.
4. If `blast_radius` is `high` or `critical`, a human-involvement record exists in the triage artifact.
5. A rollback path is declared (even if "none—write-only-artifact").
6. All required Phase 1 cluster artifacts from the PROPOSE→PLAN transition are referenced.

**Implementation**: Add `plan_validation_gate` as a callable function in `kernel.py`'s
Heartgate class, or as a standalone pre-execute check that writes to the gate ledger before
the first EXECUTE tool call. The skill `uacp-execute/SKILL.md` must reference this check
as its first step.

**Gate-ledger entry**:
```jsonl
{"gate": "PLAN_VALIDATION", "phase": "execute_preflight", "run_id": "...", "result": "pass|block", "checks": [...], "ts": "ISO8601"}
```

**Acceptance**: The 6-item checklist is documented. A test EXECUTE with a missing scope
artifact is blocked. A test EXECUTE with write_paths exceeding proposal side_effects
is blocked in enforce mode.

## Item 3.2 — Run Registry

**New path**: `state/run-registry.yaml` (maintained by `uacp-state`, read by Guardian)

**Schema**:
```yaml
kind: uacp.run_registry
last_updated: "ISO8601"
active_runs:
  - run_id: "..."
    phase: "..."
    write_paths: []     # from the run's scope artifact
    blast_radius: "..."
    started: "ISO8601"
```

**Overlap detection**: Before any run enters EXECUTE, Guardian checks the run-registry
for write-path overlap with other active runs. Overlap in `write_paths` is:
- `block` in enforce mode
- `warn` in monitor mode (with overlap details in the warning)

**Maintenance rule**: `uacp-state` is the sole writer of the run registry. It adds a run
entry at TRIAGE and removes it at RESOLVE (or when a run terminates). No other skill
or tool may write to `state/run-registry.yaml` directly.

**Acceptance**: Run registry exists. `uacp-state` SKILL.md references it as its responsibility.
Guardian blocks a simulated overlapping EXECUTE in enforce mode.

## Item 3.3 — Three Missing Documents

Write these three canonical documents and register them in `docs/index.md`.

### `docs/skill-enforcement-spec.md`

Machine-readable authority spec for each skill:
- Which Guardian tools it is authorized to call
- Which it is forbidden to call  
- What its allowed write surfaces are (aligned with Phase 1.3 YAML frontmatter)
- What its PIV contract is (aligned with Phase 1.4)
- What its phase_exit_invariants are (aligned with Phase 1.2)

This is the authoritative source that the YAML frontmatter declarations (Phase 1)
reference. If a skill frontmatter and this spec disagree, this spec wins.

Format: one section per skill, with YAML blocks for machine parsing.

### `docs/proposal-schema.md`

Full reference for the `uacp.propose` artifact kind:
- Every field with its type, required/optional status, and semantics
- Relationship between proposal fields and plan fields
  (e.g., `declared_side_effects` in proposal → `write_paths` in scope artifact)
- Validation rules (what makes a proposal viability `viable` vs `not_viable`)
- Examples for each routing outcome level

This document is the single source of truth that both the skill and any future validator
can reference. Currently the output contract lives only in the SKILL.md prose.

### `docs/lifecycle-trace-table.md`

Cross-phase artifact dependency table. For each transition:
- What artifacts must exist (inputs)
- What artifacts must be produced (outputs)
- What Heartgate checks (enforcement)
- What the gate-ledger records

Example row:
| Transition | Required inputs | Required outputs | Heartgate check | Gate-ledger gate |
|---|---|---|---|---|
| PROPOSE→PLAN | triage artifact, gate-selection artifact, proposal artifact | plan artifact, scope artifact | scope cluster pass, authority pass | PROPOSE→PLAN |
| PLAN→EXECUTE | scope artifact, plan-validation gate pass | execution checkpoint | plan-validation gate, write-path containment | PLAN_VALIDATION |

This table makes the lifecycle mechanically verifiable end-to-end.

**`docs/index.md` update**: Add all three documents to the Current Inventory table
as `reference | canonical` with appropriate update rules. Add a decision log entry
in `docs/decision-log.md` for this Phase 3 governance completeness milestone.

## Verification Checklist

Before running the Codex gate:

- [ ] Plan validation gate implemented (6-item checklist, gate-ledger recorded)
- [ ] Missing scope artifact blocks EXECUTE in enforce mode (tested)
- [ ] Exceeding proposal side_effects in write_paths blocks EXECUTE (tested)
- [ ] Run registry at `state/run-registry.yaml` with documented schema
- [ ] `uacp-state` SKILL.md references run registry as its responsibility
- [ ] Overlap detection blocks in enforce mode (simulated, documented)
- [ ] `docs/skill-enforcement-spec.md` written and covers all 7 skills
- [ ] `docs/proposal-schema.md` written with all fields, validation rules, and examples
- [ ] `docs/lifecycle-trace-table.md` written with all 6 phase transitions
- [ ] All 3 docs registered in `docs/index.md` inventory
- [ ] Decision log entry added to `docs/decision-log.md`
- [ ] All new YAML/MD files parseable
- [ ] No Phase 0–2 behavior regressed

## Codex Gate

After checklist passes, run Codex review at `tier_2_role_diverse`:
- Technical role: verify plan-validation gate coverage, run-registry overlap detection, doc-index consistency
- Governance role: verify lifecycle-trace-table covers all transitions, skill-enforcement-spec matches frontmatter
- Skeptic role: find transitions not covered in trace table, find write_paths edge cases that bypass overlap detection

**Verdict required**: `pass`, zero material findings.
**Artifact**: `verification/uacp-patch-plan-phase3-codex-review.yaml`
