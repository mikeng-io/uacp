# UACP Proposal Schema

This document is the canonical reference for the `uacp.propose` artifact. It complements `skills/devops/uacp/uacp-propose/SKILL.md` (which is the operational instruction) by defining every field's type, semantics, validation rules, and the relationship between proposal fields and downstream artifacts.

## Path convention

`proposals/{run_id}.yaml` is the canonical proposal artifact. Companion artifacts:

- `proposals/{run_id}-triage.yaml` — the triage artifact that authorized this proposal
- `proposals/{run_id}-gate-selection.yaml` — the gate-selection artifact selecting evidence clusters
- `proposals/{run_id}-intent.md` — the 1-page intent doc required by Phase 2.3

## Schema

```yaml
kind: uacp.propose                # required, string, literal
proposal_id: string               # required, unique within UACP_ROOT
run_id: string                    # required, _is_safe_run_id regex match
triage_artifact: string           # required, UACP_ROOT-relative path to triage
gate_selection_artifact: string   # optional, UACP_ROOT-relative path

title: string                     # required
purpose: string                   # required, >= 1 paragraph

authority:                        # required
  requested_by: string            # required — who asked for this work
  authorization_source: string    # required — verbatim statement or artifact citation
  escalation_required_before: string|null  # optional — phase that requires operator confirm
  escalation_reason: string|null

scope:
  in_scope: list[string]          # required, non-empty
  out_of_scope: list[string]      # optional

declared_side_effects:            # required, list of typed effects
  - kind: enum                    # file_write | file_create | state_mutation | git_commit |
                                  #   api_call | publication | irreversible_write | runtime_surface
    paths: list[string]           # required when kind in file_write|file_create|git_commit
    description: string           # required for api_call|publication|runtime_surface
    authority: string             # required, references authority block

phase_sequence: list[map]         # optional, structured phase plan when full_governance
                                  # Each entry: {phase: int, label, deliverables, review_gate, ...}

viability:
  assessment: enum                # required: viable | not_viable | needs_revision
  rationale: string               # required
  risks:                          # optional but recommended
    - id: string
      description: string
      mitigation: string

write_containment_record: string  # required — narrative describing where writes land
blocker_synthesis: string|null    # required (use "none" if no blockers)
warnings: list[string]            # optional
accepted_exceptions: list[map]    # optional
```

## Field semantics

- `run_id` MUST match `_is_safe_run_id` regex `^[A-Za-z0-9._-]{1,128}$` AND not be `.` or `..`. The kernel rejects any artifact whose `run_id` fails this check.
- `authority.authorization_source` MUST be a verbatim string or a citation to a durable source (commit hash, file path, message URL). "implied" or "inferred" values escalate to human review in `supervised_auto` and `full_auto` modes (Phase 4).
- `declared_side_effects[*].paths` MUST be UACP_ROOT-relative unless a symbolic root is declared.
- `scope.in_scope` MUST list at least one in-scope item.
- `viability.assessment == not_viable` blocks the proposal from advancing to PLAN.

## Relationship to downstream artifacts

| Proposal field | Downstream consumer | Relationship |
|---|---|---|
| `declared_side_effects[*].paths` | `plans/{run_id}-scope.yaml#write_paths` | scope.write_paths MUST be a subset of side_effects.paths (Heartgate cross-check) |
| `scope.in_scope` | plan content | plan deliverables MUST be a subset of in-scope items |
| `viability.risks` | verification cluster selection | each material risk SHOULD map to at least one cluster |
| `authority.requested_by` + `authorization_source` | every gate-ledger entry's audit record | preserved across phase transitions |
| `phase_sequence[*].deliverables` | plan execution checkpoints | plan must explicitly cover each declared phase |

## Validation rules

The kernel performs **structural** validation (kind, required fields, schema shape) only. **Semantic** validation (viability of authority, completeness of risk inventory, cluster selection adequacy) is done by the Agent Council at PROPOSE-local review.

A proposal is structurally valid when:

1. All required fields are present.
2. `run_id` passes the safe-run-id check.
3. `kind: uacp.propose` literal.
4. `authority` block is present with `requested_by` and `authorization_source` non-empty.
5. `scope.in_scope` is a non-empty list.
6. `declared_side_effects` is a list (may be empty for read-only / planning-only proposals; this is rare).
7. `viability.assessment` is one of {viable, not_viable, needs_revision}.

A proposal is operationally valid (i.e., the PLAN phase may proceed) when:

1. Structurally valid, AND
2. `viability.assessment == viable`, AND
3. No `blocker_synthesis` entries remain unresolved, AND
4. PROPOSE-local Agent Council returned `verdict: pass` (when council was selected).

## Routing-outcome examples

### `direct` (terminal_direct, no PROPOSE phase)

Direct work skips PROPOSE entirely. No proposal artifact is required.

### `lightweight`

```yaml
kind: uacp.propose
proposal_id: example-lightweight-001
run_id: example-lightweight
title: Fix typo in README
purpose: One-line typo fix
authority:
  requested_by: operator
  authorization_source: "operator said 'fix the typo'"
scope:
  in_scope: ["typo correction in README"]
declared_side_effects:
  - kind: file_write
    paths: ["README.md"]
    authority: operator authorization above
viability:
  assessment: viable
  rationale: trivially scoped, no risk
write_containment_record: only README.md modified
blocker_synthesis: none
```

### `full_governance`

See `proposals/uacp-patch-plan-20260515.yaml` for a real example. Full schema is exercised: phase_sequence, structured risks, escalation_required_before, etc.

## Authority cross-references

- `docs/reference/skill-enforcement-spec.md` — what uacp-propose may do
- `docs/reference/lifecycle-trace-table.md` — proposal's role in the lifecycle
- `engines/domain/phase_graph.py` (`LIFECYCLE_GRAPH`) — phase admissibility; `engines/domain/phase_transitions.py` (`stages_default()`) — per-phase exit invariants (codified Slice 4b; `config/phase-transitions.yaml` carries adaptive-gate doctrine only)
- `engines/domain/artifact_schema.py` (`artifact_schemas_dict()`) — sibling artifact schemas (scope, intent, lessons, evidence_disposition; `config/artifact-schemas.yaml` deleted Slice 5)
- `skills/devops/uacp/uacp-propose/SKILL.md` — operational instruction (output contract mirror)
