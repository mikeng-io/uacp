# Phase 5 Reserved Slot — Full Autonomous Mode

This document is the canonical placeholder for Phase 5 of the UACP patch plan (`proposals/uacp-patch-plan-20260515.yaml`). Phase 5 is **reserved but not scheduled** — it is the natural successor to the Phase 4 autonomous-mode stub, and it must not be entered without explicit operator authorization.

## Authority

- Run: `uacp-patch-plan-20260515`
- Proposal phase entry: `proposals/uacp-patch-plan-20260515.yaml#phase_sequence[5]`
- Status: `reserved_slot`
- Scheduling: `not_scheduled: true`

## Why Phase 5 is reserved (not implemented now)

The operator's proposal authorizes Phases 0–4 inclusive and explicitly defers Phase 5 ("Full autonomous mode") behind three prerequisites:

1. Phases 0–4 complete and Codex-reviewed (now satisfied).
2. **Three full supervised-auto UACP runs verified** (not yet performed; Phase 4 ships only the stub framework).
3. **Operator confirms Phase 5 authorization** (the proposal explicitly requires this).

Closing the patch plan at RESOLVE without entering Phase 5 honors prerequisite #3.

## What Phase 5 will deliver (per the proposal)

- **Kernel readers for `state/current.yaml#uacp_mode`** — Heartgate gates transitions on the active mode's `requires_operator_confirmation` list from `config/autonomy-policy.yaml`.
- **Trigger-ID validation** in `uacp_escalation_event` against the autonomy-policy registry.
- **Registry mutation atomicity** — atomic-rename + advisory locking for `state/run-registry.yaml` to support concurrent autonomous runs.
- **`_canonical_state_path()` kernel helper** consuming `autonomy-policy.yaml#canonical_state_paths`.
- **Push-notification surface** (Hermes core seam) replacing operator polling of `state/escalations/`.
- **`scripts/check_authority_mirror.py`** detecting drift across the config/spec/SKILL.md authority chain.
- **Structured condition DSL** for `escalation_triggers.triggers[*].condition`, replacing prose.
- **Retroactive `_advisory` audit** — every YAML field with no kernel reader either gets a reader or gets renamed with the suffix.

## Propagated constraints (Phase 5 backlog)

Phase 5, when authorized, must absorb the following propagated constraints recorded in:

- `verification/uacp-patch-plan-20260515-phase3-codex-review.yaml#propagated_constraints.to_phase_4` (17 pc_p3_* items — 9 still deferred after Phase 4)
- `verification/uacp-patch-plan-20260515-phase4-codex-review.yaml#propagated_constraints.to_phase_5` (14 pc_p4_* items)
- `verification/uacp-patch-plan-20260515-global-review.yaml#propagated_constraints.to_phase_5` (cross-phase findings, pc_g_* items)
- **Phase 0 carry-overs** (TECH-G-003): `pc_7` and `pc_8` from `verification/uacp-patch-plan-phase0-codex-review.yaml` — `live_guardian_probe.py` `guardian_blocks_unknown_plugin_mutator` (probe expects `decision: block`, actual is `block_pending_heartgate`) and `uacp_heartgate_check_passes_valid_transition` (probe artifact lacks `heartgate_coherence` block now required by transition policy). These were not in the Phase 3/4 deferred lists but remain visible failures in `scripts/live_guardian_probe.py` today. Phase 5 must either (a) remediate the probe expectations, or (b) explicitly classify them as `DEFERRED_TO_PHASE_5_OR_LATER` with an evidence pointer.

Distinct count across all sources: see the global-review verification artifact for the canonical Phase 5 backlog list with rationale and evidence pointers.

### Skill structure cleanup (out-of-band, identified 2026-05-17)

Hermes/Norty audit (full record at [`../../verification/uacp-patch-plan-20260515-skill-structure-audit.yaml`](../../verification/uacp-patch-plan-20260515-skill-structure-audit.yaml)) flagged the post-restructure SKILL.md files at `HERMES_ROOT/skills/devops/uacp/uacp-*/SKILL.md` as still 11–15 KB each — too large for ACP-style lean conductors. Recommendation: split each phase skill into `SKILL.md` (lean conductor; ≤4 KB target) + `references/` (contract, checklist, pitfalls, mode-behavior) + `schemas/` + `scripts/`. Start with `uacp-verify` as the template since it's both large and authority-sensitive.

This is **out-of-band** for the UACP_ROOT-versioned codebase (skills live under `HERMES_ROOT/`, not under UACP_ROOT). Track as `pc_g_skill_structure_cleanup` in the Phase 5 backlog. Sibling concerns flagged by the same audit (root `references/` quarantine status; broken relative links in some `SKILL.md` cross-references; lack of git-tracking provenance for the canonical skill source) are subsumed under the same constraint and itemized in the audit artifact's `related_findings` block.

## Activation procedure

When the operator decides to schedule Phase 5:

1. Run three supervised-auto UACP runs end-to-end (TRIAGE→RESOLVE) and verify that:
   - Every transition emits the documented gate-ledger entries.
   - Every PLAN→EXECUTE transition's PLAN_VALIDATION record carries explicit per-check pass evidence.
   - Every active run registers in `state/run-registry.yaml` after PLAN_VALIDATION and deregisters at RESOLVE.
   - Every operator-engaging condition emits a `uacp_escalation_event` record.
2. Open a new patch-plan run (`uacp-patch-plan-NNNNNNNN`) whose Phase 5 deliverables match this document.
3. Confirm authorization explicitly in the new proposal's `authority.authorization_source` field.
4. Begin Phase 5 with a council-driven design pass (technical/governance/skeptic) on the kernel-reader landing surface, since this is the moment `uacp_mode` becomes load-bearing.

## What is NOT in Phase 5

- Cross-runtime adapters (OpenCode, Codex, Gemini Code Assist). Those are independent UACP work.
- Operator UI / dashboard. UACP is runtime-neutral.
- Knowledge Bank promotion beyond `outputs/{run_id}-lessons.yaml#applies_to_future_runs`. That is a separate roadmap.

## Provenance

This reserved-slot document is generated by the RESOLVE phase of run `uacp-patch-plan-20260515`. The patch plan itself closes here; Phase 5 will be a fresh run.
