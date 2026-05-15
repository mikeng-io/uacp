# Phase 2 — Artifact Structure

**Phase**: 2 of 4 (Phases 0–4 scheduled)
**Granularity**: 6
**Plugin-only**: yes (no Hermes core changes)
**Prerequisite**: Phase 1 Codex gate passed; drift-reconciliation step completed
**Commit boundary**: one atomic commit after Codex gate passes

## Drift Reconciliation (First Step)

Read `verification/uacp-patch-plan-phase1-codex-review.yaml` before starting any work.
Classify all findings and update this phase's scope for any `propagated_constraint` findings,
particularly any vocabulary or field-name reconciliations between the gate-ledger schema
and the artifact schemas introduced in this phase.

## Item 2.1 — Scope Artifact Schema

**New kind**: `uacp.scope`
**Required path**: `plans/{run_id}-scope.yaml` (produced at end of PLAN phase, before EXECUTE)

**Schema**:
```yaml
kind: uacp.scope
run_id: "..."
write_paths: []          # explicit files or dirs that MAY be written
read_paths: []           # explicit files or dirs that MAY be read
forbidden_paths: []      # paths that MUST NOT be touched
api_surfaces: []         # external API calls authorized (service, endpoint, method)
runtime_surfaces: []     # external processes authorized (command pattern)
migrations: []           # schema/DB changes authorized
side_effects: []         # other declared effects (publication, notification, etc.)
blast_radius: low | medium | high | critical
rollback_path: "..."     # how to undo; "none—write-only-artifact" if not reversible
```

**Guardian enforcement**: The containment check in `kernel.py` must compare every file
write event against `write_paths` from the active run's scope artifact. Writes outside
`write_paths` get blocked in enforce mode, warned in monitor mode. This closes the gap
where write containment is a documented invariant but not a mechanically enforced one.

**Loading**: Guardian loads the scope artifact on first use in an EXECUTE phase by reading
`{uacp_root}/plans/{run_id}-scope.yaml`. If the file is absent in EXECUTE, it blocks
in enforce mode.

**Acceptance**: The schema is documented in `config/phase-transitions.yaml` or a new
`config/artifact-schemas.yaml`. Guardian loads and checks write_paths during EXECUTE.
A test write outside write_paths is blocked in enforce mode.

## Item 2.2 — Evidence Disposition Pairs

**Pattern**: Each verification cluster that runs produces two companion files.

**File 1**: `verification/{run_id}-{cluster}-verified-facts.md`
```markdown
# Verified Facts — {cluster} — {run_id}

Each entry is a confirmed assertion with a source evidence reference.

| Fact | Source |
|---|---|
| ... | path/to/artifact or tool output |
```

**File 2**: `verification/{run_id}-{cluster}-assumptions.md`
```markdown
# Assumptions — {cluster} — {run_id}

Each entry is an accepted assertion that was not directly verified.
Disposition must be explicit.

| Assumption | Disposition | Owner | Next-phase obligation |
|---|---|---|---|
| ... | accepted_risk | ... | ... |
| ... | deferred | ... | revisit in VERIFY |
| ... | pending | ... | MUST be resolved before RESOLVE |
```

**Heartgate enforcement**: The VERIFY→RESOLVE Heartgate check must confirm:
- Both files exist for all required clusters.
- No row in any assumptions file has disposition `pending` without a recorded owner and
  next-phase obligation. An unowned `pending` is a block, not a warn.

**Acceptance**: Both file schemas are documented. Heartgate blocks on missing disposition-pair
files. Heartgate blocks on unowned `pending` assumptions in verify→resolve transition.

## Item 2.3 — Run Intent Doc

**New kind**: `uacp.intent`
**Required path**: `proposals/{run_id}-intent.md` (produced at end of TRIAGE, before PROPOSE)

**Schema**:
```markdown
# Run Intent — {run_id}

## Success Definition
What does a complete, successful run look like? (1-3 sentences, concrete)

## Explicit Out-of-Scope
What is explicitly excluded from this run? (bulleted list)

## Termination Condition
When should this run stop even if not fully complete?
(e.g., "Stop if the scope artifact cannot be written without Hermes core changes")

## Authority Source
(one line: who authorized and what statement)
```

**Purpose**: Feeds into RESOLVE lessons and into autonomous mode's scope-bounding logic
(Phase 4). The termination condition is particularly important for supervised-auto and
full-auto modes where the system needs a machine-readable stop condition.

**Acceptance**: The schema is documented. `uacp-triage` SKILL.md references the intent doc
as a required output. Phase 0 triage artifact for this run demonstrates the pattern
(retroactively: add the intent content to the existing triage artifact or as a companion).

## Item 2.4 — Structured Lessons Pattern

**New kind**: `uacp.lessons`
**Required path**: `knowledge/lessons/{run_id}-lessons.yaml` (produced at RESOLVE)
**Auto-copy rule**: Entries with `applies_to_future_runs: true` are also written to
`knowledge/lessons/universal-{category}-lessons.yaml` (append, not overwrite) as the
seed of the Knowledge Bank retrieval path.

**Schema**:
```yaml
kind: uacp.lessons
run_id: "..."
lessons:
  - id: "..."
    category: governance | technical | process | tooling | enforcement
    finding: "..."         # what happened (neutral description)
    recommendation: "..."  # what to do differently
    gate_affected: "..."   # which gate/phase this applies to
    applies_to_future_runs: true | false
    knowledge_path: "knowledge/lessons/..."  # where it lands if applies_to_future_runs
```

`uacp-resolve/SKILL.md` gets a reference to this schema as a required output pattern.

**Acceptance**: Schema documented. `uacp-resolve` SKILL.md references it. At least one
entry in the current run's lessons file demonstrates the pattern correctly.

## Verification Checklist

Before running the Codex gate:

- [ ] Scope artifact schema documented (config or dedicated artifact-schemas file)
- [ ] Guardian loads scope artifact and checks write_paths in EXECUTE phase
- [ ] Out-of-scope write test blocked in enforce mode
- [ ] Evidence disposition pair schemas documented
- [ ] Heartgate blocks VERIFY→RESOLVE on missing disposition-pair files
- [ ] Heartgate blocks on unowned `pending` assumptions
- [ ] Run intent doc schema documented
- [ ] `uacp-triage` SKILL.md references intent doc as required output
- [ ] Structured lessons schema documented
- [ ] `uacp-resolve` SKILL.md references lessons as required output
- [ ] All new schemas consistent with existing transition artifact vocabulary (drift check)
- [ ] All new YAML/MD schemas parseable
- [ ] No Phase 0–1 behavior regressed

## Codex Gate

After checklist passes, run Codex review at `tier_2_role_diverse`:
- Technical role: verify Guardian scope-artifact loading, write-path check, Heartgate disposition-pair enforcement
- Governance role: verify intent doc termination condition is sufficient for autonomous mode (Phase 4 forward compatibility)
- Skeptic role: find cases where write_paths is ambiguous (glob vs exact, directory vs file), disposition `pending` escape routes

**Verdict required**: `pass`, zero material findings.
**Artifact**: `verification/uacp-patch-plan-phase2-codex-review.yaml`
