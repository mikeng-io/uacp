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
| — | Doc subdirectory + ADR restructure | [ADR-0008](docs/architecture/0008-doc-structure-and-adr-adoption.md) | 8 commits: `d6efc43` through `fec2c8d` inclusive | 2026-05-17 |
| — | Adaptive proposal & plan packages | [ADR-0009](docs/architecture/0009-adaptive-proposal-and-plan-packages.md) | `f1256ae` | 2026-05-19 |
| — | Operator phase-return presentation | [ADR-0010](docs/architecture/0010-operator-phase-return-presentation.md) | `01a441e` | 2026-05-19 |
| — | Semantic-package artifacts | [ADR-0011](docs/architecture/0011-semantic-package-artifacts.md) | `600e82d` | 2026-05-19 |
| — | Phase Intent Verification (PIV) — execute evidence gate | [ADR-0012](docs/architecture/0012-phase-intent-verification.md) | `a7648d0` | 2026-05-19 |
| — | Adaptive VERIFY evidence | [ADR-0013](docs/architecture/0013-adaptive-verify-evidence.md) | `cc39deb` | 2026-05-20 |
| — | Adaptive RESOLVE closure | [ADR-0014](docs/architecture/0014-adaptive-resolve-closure.md) | `2926ae0` | 2026-05-20 |
| — | Web backends separate from bridge adapters | [ADR-0015](docs/architecture/0015-web-backends-separate-from-bridge-adapters.md) | `e925e28` | 2026-06-08 |
| — | Config-collapse (Slices 2–5): phase-transition grammar codified into `skills/uacp-core/scripts/engines/domain/`; knobs in `config/uacp.toml`; doctrine stays YAML | — | `b4acb36` (Slice 5 merge) | 2026-06-16 |
| — | Goal-driven track — second lifecycle track (semantic/exploratory work) | [ADR-0016](docs/architecture/0016-goal-driven-track.md) | `418cb93` | 2026-06-16 |
| — | Skill-authoring convention | [ADR-0017](docs/architecture/0017-skill-authoring-convention.md) | `57ed772` | 2026-06-16 |
| — | Skill structure cleanup: phase skills split into `SKILL.md` (lean conductor) + `references/` + `schemas/` + `scripts/`; uacp-verify decomposed as template; `domain-registry` folded into `uacp-core/references/domains/`; ADR-0017 codified the convention | [ADR-0017](docs/architecture/0017-skill-authoring-convention.md) | `86d99e9` (Step 2 complete) | 2026-06-17 |
| — | Brainstorm optional phase + lesson/knowledge corpus + Oracle retrieval engine — built & merged; Oracle ships inert (`[oracle] enabled = false` in `config/uacp.toml`); knowledge/lessons corpora live under `.uacp/` | — | `5abe0f4` (C-floor merge) / `1bf68d3` (C-semantic merge) | 2026-06-17 |
| — | docs/ OKF frontmatter enforcement + doc-architecture refresh (in progress) | — | `b66c5e7` | 2026-06-18 |

## 🚧 Reserved (not scheduled)

### Phase 5 — Full autonomous mode

**Status**: reserved_slot. **Prerequisites**: three verified `supervised_auto` runs + explicit operator authorization (see [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md)).

#### Phase 5 backlog (propagated constraints)

The canonical Phase 5 backlog is composed of constraints propagated from the prior phases. Source of truth: the verification YAMLs were previously under `verification/` and `executions/`; those top-level directories have been migrated to `.uacp/` (see `.uacp/lessons/` for active artifacts). The snapshot counts below remain valid; consult `git log` for the originating commits if a precise pointer is needed.

| Source | Constraints |
|---|---|
| Phase 3 review | 18 pc_p3_* items declared; 9 reclassified DEFERRED_TO_PHASE_5 after Phase 4 |
| Phase 4 review | 19 pc_p4_* items |
| Global review | 15 pc_g_* items |
| Phase 0 carry-overs | pc_7, pc_8 (live_guardian_probe failures — see [`docs/plans/phase5-reserved-slot.md`](docs/plans/phase5-reserved-slot.md)) |

The counts above are snapshots. The live list and any reclassifications live in the originating commits; the `.uacp/lessons/` corpus is the active runtime home.

#### Phase 5 thematic groupings

The propagated backlog clusters into five themes:

1. **Kernel readers for autonomy-policy** — make `uacp_mode`, `escalation_triggers`, `canonical_state_paths`, mode-conditional Heartgate behavior actually load-bearing (today they are `enforcement_status: stub_only_phase_4`).
2. **Run-registry atomicity** — atomic-rename + advisory locking + scope-existence precheck before supervised_auto runs are activated.
3. **Drift detection** — `scripts/check_authority_mirror.py` enforcing tool / config / SKILL.md / spec coherence; pinned drift-classification vocabulary.
4. **Doctrine completeness** — Phase 4 surface coverage in `runtime-enforcement.md`, `proposal-schema.md`, `lifecycle-reference.md`, `orchestration-model.md`; complete `_advisory` audit.
5. **Phase 5 entry gate** — mechanical refusal of Phase 5 EXECUTE until three supervised-auto runs are recorded in `.uacp/state/runs/`.

## 🔭 Speculative (not yet scoped)

- **Cross-runtime adapters**: Bridge contracts for Claude Code, Codex, Kimi, Gemini, and OpenCode now exist under `skills/uacp-bridge/references/`. All five runtimes have substantive reference docs. No further adapter work is currently scoped.
- **Oracle live mode**: Oracle ships inert (`[oracle] enabled = false`). A live model run + reranker bake-off script (`skills/uacp-core/scripts/oracle/`) are implemented but not activated. Enabling in production requires an operator decision.
- **Operator UI / dashboard**: not scoped. UACP is runtime-neutral; a dashboard is a deployment concern, not a core deliverable.
- **Knowledge Bank promotion beyond `lessons.applies_to_future_runs`**: the auto-copy mechanism was scoped to Phase 2 but landed as schema-only. The Oracle corpus-ownership boundary (`.uacp/knowledge/`, `.uacp/lessons/`) is now established; promotion logic could be completed in Phase 5 or a separate run.
