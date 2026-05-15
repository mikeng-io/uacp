# Phase 4 — Autonomous Mode Slot

**Phase**: 4 of 4 (Phases 0–4 scheduled)
**Granularity**: 7
**Plugin-only**: mostly (one Hermes core seam required — stub only in this phase)
**Prerequisite**: Phase 3 Codex gate passed; drift-reconciliation step completed;
  **OPERATOR CONFIRMATION REQUIRED** before Phase 4 begins (see escalation below)
**Commit boundary**: one atomic commit after Codex gate passes

## Operator Escalation (Before Any Phase 4 Work)

Phase 4 introduces the async escalation surface — the one seam that touches Hermes beyond
the plugin boundary. Before Phase 4 begins, confirm with the operator:

1. Is the stub approach acceptable for Phase 4?
   (Stub: escalation writes to `state/escalations/`, operator polls. Full push notification is Phase 5.)
2. Is `full_auto` mode acceptable as a reserved schema slot only, with no behavior implemented?
3. Is `supervised_auto` mode acceptable with escalation detection but no real-time notification?

If the operator confirms, proceed. If the operator requests a different approach, update
this plan before implementation.

## Drift Reconciliation (First Step After Confirmation)

Read `verification/uacp-patch-plan-phase3-codex-review.yaml`.
Classify all findings. Pay particular attention to any vocabulary or schema changes
that Phase 3's review required — `uacp_mode` field names and escalation trigger taxonomy
must be consistent with all earlier artifacts.

## Item 4.1 — `uacp_mode` in State Schema

**Architecture insight**: `full_auto` is NOT looser governance — it is the strictest mode
because there is no human fallback. Guardian must enforce everything mechanically.
The mode ladder moves toward stricter enforcement as autonomy increases.

**File**: `state/current.yaml` and `config/state.yaml` (schema documentation)

Add `uacp_mode` field with four values:
```yaml
uacp_mode: manual | semi_auto | supervised_auto | full_auto
```

| Mode | Human role | Guardian role | Phase 4 status |
|---|---|---|---|
| `manual` | Drives every phase | Enforces boundaries | Fully implemented (current) |
| `semi_auto` | Approves phase transitions only | Enforces boundaries + phase contracts | Implementable with Phase 0–3 deliverables |
| `supervised_auto` | Only for escalation triggers | Full enforcement + escalation detection | Stub in Phase 4; full in Phase 5 |
| `full_auto` | None (certified domains only) | Sole authority + escalation owner | Reserved slot only; not implemented |

**Default**: `manual` (preserves all existing behavior).

Update `state/current.yaml` to include `uacp_mode: manual` as the current state.
Document the field in `config/state.yaml` with the four-value enum and the mode ladder.

**Acceptance**: `uacp_mode` field exists in state schema documentation and in
`state/current.yaml`. All existing behavior unchanged (default is `manual`).

## Item 4.2 — Autonomy Policy Config

**New file**: `config/autonomy-policy.yaml`

```yaml
kind: uacp.autonomy_policy
schema_version: '0.1'
purpose: >
  Defines escalation triggers that activate human involvement regardless of uacp_mode.
  In supervised_auto and full_auto, these triggers produce a blocking decision and
  an escalation record rather than proceeding.

escalation_triggers:
  - id: granularity_ceiling
    condition: composite_granularity >= 8
    escalate_to: human_decision
    modes_affected: [supervised_auto, full_auto]
    rationale: High-granularity work requires human judgment by policy.

  - id: external_side_effect
    condition: "side_effects contains api_surface | publication | irreversible_write"
    escalate_to: human_decision
    modes_affected: [semi_auto, supervised_auto, full_auto]
    rationale: External effects cannot be undone; human confirmation required.

  - id: authority_unclear
    condition: authorization_source == "inferred"
    escalate_to: human_decision
    modes_affected: [supervised_auto, full_auto]
    rationale: Inferred authority is insufficient for autonomous action.

  - id: guardian_block_unresolved
    condition: "guardian_decision == block AND no accepted_exception"
    escalate_to: human_decision
    modes_affected: [all]
    rationale: Unresolved Guardian block must always surface to human.

  - id: piv_second_failure
    condition: piv_attempt == 2 AND piv_result == fail
    escalate_to: human_decision
    modes_affected: [supervised_auto, full_auto]
    rationale: Repeated PIV failure indicates something is wrong that automation cannot self-correct.

  - id: overlap_detected
    condition: run_registry_overlap == true
    escalate_to: human_decision
    modes_affected: [supervised_auto, full_auto]
    rationale: Concurrent write-path overlap requires human arbitration.

  - id: scope_exceeded
    condition: "write attempt outside write_paths"
    escalate_to: human_decision
    modes_affected: [supervised_auto, full_auto]
    rationale: Out-of-scope write in autonomous mode is a hard stop.

certified_domains: []
notes: >
  certified_domains is reserved for Phase 5. It will list domains where full_auto is
  operator-authorized. An empty list means full_auto is not currently certified for
  any domain.
```

Guardian reads this config in pre-tool-call evaluation. In `supervised_auto` and
`full_auto`, a matching escalation trigger produces a blocking decision and writes
an escalation record.

**Acceptance**: File exists, parses, and is loaded by Guardian. A simulated trigger
(e.g., set composite_granularity=9 in a test event) produces a block with escalation
classification in supervised_auto mode.

## Item 4.3 — Mode-Aware Skill Behavior Stubs

**Target files**: all 7 SKILL.md files (add `mode_behavior` block to YAML frontmatter)

```yaml
mode_behavior:
  manual: >
    Prompt operator at each checkpoint. Await approval before phase gate.
  semi_auto: >
    Execute phase autonomously. Pause at phase gate for operator transition approval.
    Report completion; do not auto-advance.
  supervised_auto: >
    Execute autonomously. Pause only on escalation trigger. Write escalation record
    to state/escalations/; await operator response before continuing.
    [STUB — behavior not yet implemented beyond escalation detection]
  full_auto: >
    Execute autonomously without operator prompts. Guardian is sole authority.
    Escalation triggers activate human loop. Certified domains only.
    [RESERVED SLOT — not implemented in Phase 4]
```

The stubs serve two purposes:
1. They make the interface explicit so Phase 5 can fill in behavior without a breaking change.
2. They make the current operating mode machine-readable for future Guardian policy evaluation.

**Acceptance**: All 7 skills have `mode_behavior` in frontmatter. Existing behavior
(manual mode) is unchanged.

## Item 4.4 — Escalation Event Tool Stub

**New Guardian tool**: `uacp_escalation_event`
**Write path**: `state/escalations/{run_id}-{trigger_id}-{ts}.yaml`

Schema:
```yaml
kind: uacp.escalation_event
run_id: "..."
trigger_id: "..."
trigger_condition: "..."
mode_at_time: "..."
phase_at_time: "..."
blocking: true
resolution: null   # filled by operator or Phase 5 push mechanism
ts: "ISO8601"
```

In Phase 4, this tool writes the file and blocks execution until the operator sets
`resolution` manually. Phase 5 replaces the polling model with a real-time push notification.

**Acceptance**: Tool registered and callable. A test escalation event writes the file
correctly. Guardian in `supervised_auto` mode triggers the tool and blocks on an
unresolved escalation.

## Verification Checklist

Before running the Codex gate:

- [ ] Operator confirmed Phase 4 approach (stub escalation, full_auto as reserved slot)
- [ ] `uacp_mode` field in state schema documentation and `state/current.yaml`
- [ ] Default mode is `manual`; all existing behavior unchanged
- [ ] `config/autonomy-policy.yaml` written and loads in Guardian
- [ ] Test trigger (granularity >= 8) produces block + escalation in supervised_auto mode
- [ ] All 7 skills have `mode_behavior` stubs in frontmatter
- [ ] `uacp_escalation_event` tool registered and callable
- [ ] Escalation file written correctly, blocks until resolved
- [ ] `config/autonomy-policy.yaml` registered in `docs/index.md` inventory
- [ ] Decision log entry for Phase 4 in `docs/decision-log.md`
- [ ] Phase 5 reserved slot is clearly documented (not a stub to implement — a deliberate deferral)
- [ ] All modified files parse without error
- [ ] No Phase 0–3 behavior regressed

## Codex Gate

After checklist passes, run Codex review at `tier_2_role_diverse`:
- Technical role: verify escalation trigger evaluation, tool registration, state write path safety
- Governance role: verify mode ladder is correctly ordered (stricter as autonomy increases), reserved-slot documentation is unambiguous
- Skeptic role: find triggers that could produce infinite escalation loops, modes that have no behavioral difference from adjacent modes, full_auto escape routes that bypass Guardian

**Verdict required**: `pass`, zero material findings.
**Artifact**: `verification/uacp-patch-plan-phase4-codex-review.yaml`

---

## After Phase 4 Closes

Phase 4 completion marks the end of the scheduled patch plan. The system is now at
`semi_auto` capability with `supervised_auto` stubs ready.

**Before Phase 5 can begin**:
1. Run three full UACP lifecycle runs in `semi_auto` mode; all must complete without
   Guardian blocks or PIV double-failures.
2. Operator explicitly authorizes Phase 5.
3. A new UACP run is opened for Phase 5 (it is not a continuation of this run).
