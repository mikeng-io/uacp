# Phase 1 — Mechanical Pre-Flight Contracts

**Phase**: 1 of 4 (Phases 0–4 scheduled)
**Granularity**: 7
**Plugin-only**: yes (no Hermes core changes)
**Prerequisite**: Phase 0 Codex gate passed; drift-reconciliation step completed
**Commit boundary**: one atomic commit after Codex gate passes

## Drift Reconciliation (First Step)

Read `verification/uacp-patch-plan-phase0-codex-review.yaml` before starting any work.
Classify all findings and update this phase's scope if any `propagated_constraint` findings
require expanding or narrowing the deliverables below.

## Item 1.1 — Gate Ledger

**New path**: `state/gate-ledger/<run-id>.jsonl` (append-only JSONL, one record per gate evaluation)

**Record schema**:
```jsonl
{"gate": "TRIAGE→PROPOSE", "run_id": "...", "phase": "triage", "result": "pass|warn|block", "invariants": [...], "clusters": [...], "piv_attempt": null, "ts": "ISO8601", "reviewer": "model|codex|operator"}
```

**New Guardian tool**: `uacp_gate_ledger_append`
- Registered in the plugin tool registry alongside existing UACP writer tools
- Accepts: `run_id`, `gate`, `record` (the JSONL dict)
- Enforces: path must be `state/gate-ledger/{run_id}.jsonl`; opens in append mode only;
  rejects any operation that would seek, truncate, or overwrite the file
- Returns: the byte offset of the written record (proof of append)

**Acceptance**: `state/gate-ledger/` directory exists with schema documented in
`config/state.yaml`. The `uacp_gate_ledger_append` tool is registered and callable.
A test run appends two records and confirms the file contains both in order.

## Item 1.2 — Phase Exit Invariant Declarations

**Target files**: each of the 7 SKILL.md files (YAML frontmatter block)

Add `phase_exit_invariants:` to each skill's YAML frontmatter. This is a machine-readable
list that Heartgate checks before passing any transition FROM this phase.

Example for `uacp-plan/SKILL.md`:
```yaml
phase_exit_invariants:
  - artifact: plans/{run_id}-scope.yaml
    required_fields: [write_paths, blast_radius, rollback_path]
  - artifact: state/gate-ledger/{run_id}.jsonl
    contains_gate: PROPOSE→PLAN
  - verification_cluster: scope
    min_state: pass
  - piv_result: pass
```

Guardian's Heartgate check (`uacp_heartgate_check`) must load these declarations from
the active phase's skill frontmatter and evaluate each invariant before returning a
transition verdict. If a declared artifact is missing, Heartgate blocks (not warns)
regardless of `guardian_mode`.

**Implementation note**: The skill YAML frontmatter must be parseable by the Heartgate
kernel. Confirm `kernel.py`'s Heartgate implementation reads from the skill registry or
from a skill-frontmatter file, not from inline invocation arguments only.

**Acceptance**: All 7 skills have `phase_exit_invariants`. Heartgate blocks when a
declared artifact is absent. Existing phase transitions with all artifacts present still pass.

## Item 1.3 — Allowed-Tools and Forbidden-Tools Declarations

**Target files**: each of the 7 SKILL.md files (YAML frontmatter block)

Add to each skill's frontmatter:
```yaml
allowed_tools:
  - read_file
  - search_files
  - uacp_doc_write         # example — varies per skill
  - uacp_heartgate_check
forbidden_tools:
  - uacp_state_write       # example — only uacp-state and uacp-execute may use this
  - execute_code           # example — only uacp-execute may use this
```

Guardian's pre-tool-call handler checks the active phase (from `task_uacp_context.uacp_phase`)
against the relevant skill's tool declarations. A forbidden tool call in a phase gets
blocked in enforce mode, warned in monitor mode, logged in audit mode.

The skill-level enforcement spec (Phase 3, `docs/skill-enforcement-spec.md`) is the
authoritative source. Phase 1 adds the frontmatter declarations; Phase 3 writes the
full spec document.

**Acceptance**: Each skill has `allowed_tools` and `forbidden_tools` in its frontmatter.
Guardian blocks a forbidden-tool test call in enforce mode. Monitor mode produces a warn,
not a block.

## Item 1.4 — PIV (Post-Phase Verification) Protocol

**Definition**: A 5-point self-evaluation run by the model at the end of every phase,
before Heartgate is called. Result is recorded as a gate-ledger entry.

**5 PIV checks**:
1. Did the phase produce all artifacts declared in `phase_exit_invariants`?
2. Do those artifacts satisfy the plan/proposal that authorized this phase?
3. Are all material council findings classified in `handled_findings_chain`?
4. Are non-waivable invariants still intact (spot-check: authority, write containment, traceable state)?
5. Did the phase introduce any new material findings that remain unresolved?

**Gate-ledger record** for a PIV run:
```jsonl
{"gate": "PIV", "phase": "plan", "run_id": "...", "piv_attempt": 1, "result": "pass|fail", "checks": [...], "ts": "ISO8601"}
```

**Enforcement rule**:
- PIV attempt 1 fails → model remediates and runs PIV attempt 2.
- PIV attempt 2 fails → Heartgate blocks the transition unconditionally (no warn path).
  This requires a re-plan or operator intervention.
- PIV attempt 2 pass → transition proceeds to Heartgate.

Add this rule to `config/phase-transitions.yaml` under `transition_rule`:
```yaml
piv_rule:
  max_attempts: 2
  second_failure_action: block_unconditional
  ledger_required: true
```

**Acceptance**: `config/phase-transitions.yaml` contains the PIV rule. Gate-ledger records
PIV results. A simulated double-failure PIV blocks Heartgate unconditionally (test in code
or manual dry-run documented in verification).

## Verification Checklist

Before running the Codex gate:

- [ ] `state/gate-ledger/` directory exists, schema in `config/state.yaml`
- [ ] `uacp_gate_ledger_append` tool registered and callable, append-only enforced
- [ ] All 7 skills have `phase_exit_invariants` in YAML frontmatter
- [ ] Heartgate reads frontmatter invariants and blocks on missing artifacts
- [ ] All 7 skills have `allowed_tools` and `forbidden_tools` in YAML frontmatter
- [ ] Guardian pre-tool-call checks tool against active-phase declarations
- [ ] PIV protocol defined in `config/phase-transitions.yaml`
- [ ] Gate-ledger records PIV results with attempt number
- [ ] Double-failure PIV triggers unconditional Heartgate block (tested or dry-run documented)
- [ ] All modified Python files parse without syntax error
- [ ] All modified YAML files parse without error
- [ ] No Phase 0 behavior regressed (re-run Phase 0 tests)

## Codex Gate

After checklist passes, run Codex review at `tier_2_role_diverse`:
- Technical role: verify gate-ledger append-only enforcement, Heartgate frontmatter integration, tool-check logic
- Governance role: verify PIV 5-check coverage is sufficient, double-failure rule is unambiguous
- Skeptic role: find edge cases in tool-check (phase not set, phase mismatch, unknown phase), PIV timing gaps

**Verdict required**: `pass`, zero material findings.
**Artifact**: `verification/uacp-patch-plan-phase1-codex-review.yaml`
