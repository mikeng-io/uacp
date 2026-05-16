# UACP Roadmap

Forward-looking work organized by readiness. Items at the top are scheduled and authorized; items further down are reserved or speculative.

For each phase's deliverables, see the corresponding ADR in [`docs/architecture/`](docs/architecture/INDEX.md). For the live propagated-constraint backlog (the source of truth for Phase 5 work), see the verification YAMLs cited under each phase.

## ✅ Completed

| Phase | Title | ADR | Commit | Date |
|---|---|---|---|---|
| 0 | Wire filesystem_guard_verified, real policy.mode, classify governed tools | [ADR-0002](docs/architecture/0002-phase0-policy-mode-and-classification.md) | `696e184` | 2026-05-15 |
| 1 | Mechanical pre-flight contracts (gate ledger, Layer B, phase exit invariants, PIV) | [ADR-0003](docs/architecture/0003-phase1-gate-ledger-layer-b-piv.md) | `49d8929` | 2026-05-15 |
| 2 | Structured artifact schemas with Heartgate enforcement | [ADR-0004](docs/architecture/0004-phase2-artifact-schemas.md) | `a0644b0` | 2026-05-15 |
| 3 | plan_validation_gate, run_registry, authority docs | [ADR-0005](docs/architecture/0005-phase3-plan-validation-gate-and-run-registry.md) | `bee42cd` | 2026-05-15 |
| 4 | uacp_mode, autonomy-policy, escalation-event stub | [ADR-0006](docs/architecture/0006-phase4-autonomous-mode-stub.md) | `3c48406` | 2026-05-16 |
| — | Global cross-phase audit + R1/R2 remediation | [ADR-0007](docs/architecture/0007-global-review-cross-phase-remediation.md) | `93dba83` / `da5c15f` | 2026-05-17 |
| — | Doc subdirectory + ADR restructure | [ADR-0008](docs/architecture/0008-doc-structure-and-adr-adoption.md) | (in-flight) | 2026-05-17 |

## 🚧 Reserved (not scheduled)

### Phase 5 — Full autonomous mode

**Status**: reserved_slot. **Prerequisites**: three verified `supervised_auto` runs + explicit operator authorization (see [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md)).

#### Phase 5 backlog (propagated constraints)

The canonical Phase 5 backlog is composed of constraints propagated from the prior phases. Source of truth:

| Source | Constraints |
|---|---|
| Phase 3 review | 8 of 17 pc_p3_* still deferred (`verification/uacp-patch-plan-20260515-phase3-codex-review.yaml#propagated_constraints.to_phase_4`) |
| Phase 4 review | 14 pc_p4_* (`verification/uacp-patch-plan-20260515-phase4-codex-review.yaml#propagated_constraints.to_phase_5`) |
| Global review | pc_g_* (`verification/uacp-patch-plan-20260515-global-review.yaml#deferred_to_phase_5_with_evidence_pointer`) |
| Phase 0 carry-overs | pc_7, pc_8 (live_guardian_probe failures — see [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md)) |

#### Phase 5 thematic groupings

The propagated backlog clusters into five themes:

1. **Kernel readers for autonomy-policy** — make `uacp_mode`, `escalation_triggers`, `canonical_state_paths`, mode-conditional Heartgate behavior actually load-bearing (today they are `enforcement_status: stub_only_phase_4`).
2. **Run-registry atomicity** — atomic-rename + advisory locking + scope-existence precheck before supervised_auto runs are activated.
3. **Drift detection** — `scripts/check_authority_mirror.py` enforcing tool / config / SKILL.md / spec coherence; pinned drift-classification vocabulary.
4. **Doctrine completeness** — Phase 4 surface coverage in `runtime-enforcement.md`, `proposal-schema.md`, `lifecycle-reference.md`, `orchestration-model.md`; complete `_advisory` audit.
5. **Phase 5 entry gate** — mechanical refusal of Phase 5 EXECUTE until three supervised-auto runs are recorded in `state/runs/`.

### Skill structure cleanup (out-of-band, identified during global review)

Hermes audit (2026-05-17) flagged the post-restructure skill SKILL.md files at `HERMES_ROOT/skills/devops/uacp/uacp-*/SKILL.md` as still 11–15KB each — too large for ACP-style lean conductors. Recommendation: split each phase skill into `SKILL.md` (lean conductor) + `references/` (contract, checklist, pitfalls, mode-behavior) + `schemas/` + `scripts/`. Start with uacp-verify as the template since it's both large and authority-sensitive.

This is **out-of-band** for the UACP_ROOT-versioned codebase (skills live under HERMES_ROOT). Track as: `pc_g_skill_structure_cleanup`.

## 🔭 Speculative (not yet scoped)

- **Cross-runtime adapters**: OpenCode, Codex, Gemini Code Assist. Independent of Phase 5; would benefit from the kernel readers Phase 5 lands.
- **Operator UI / dashboard**: not scoped. UACP is runtime-neutral; a dashboard is a deployment concern, not a core deliverable.
- **Knowledge Bank promotion beyond `lessons.applies_to_future_runs`**: the auto-copy mechanism was scoped to Phase 2 but landed as schema-only. Phase 5 (or a separate run) could complete it.
