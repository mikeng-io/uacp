# UACP Knowledge

Durable run-lessons, design rationale, and history — relocated from the former
`skills/references/` shared dump (abolished in the skill-convention application,
ADR-0017 / Step 2 Slice 3).

**Not skill-citable.** Skills must reference only files that ship with a skill
(their own `references/`, or `uacp-core/references/`). These knowledge docs are for
human and agent *reading* and *provenance*, not skill instruction prose. Operational
contracts that a skill needs live under `uacp-core/references/`, not here.

## Index

- [adaptive-gate-selection-rationale.md](adaptive-gate-selection-rationale.md) — Why UACP uses domain-adaptive gates instead of a fixed checklist; meta-gate flow, domain-specific VERIFY examples (software/marketing/research/productivity), non-waivable invariants. Live implementation: `config/gate-selection.yaml`.
- [agent-council-integration-and-operationalization-lessons.md](agent-council-integration-and-operationalization-lessons.md) — Split-plan shape, cognitive-plane anti-patterns, phase-local granularity fields, surface taxonomy, skill/validator propagation, and PLAN→EXECUTE checklist for Agent Council work.
- [branch-porting-ground-truthing.md](branch-porting-ground-truthing.md) — Read-canon-first rule, four-category diff classification (already-present/missing/conflicting/impl-detail-only), canon read order, "skills are implementation surfaces; UACP is the authority layer" pitfall.
- [claude-code-print-mode-adversarial-review.md](claude-code-print-mode-adversarial-review.md) — 3-line recipe: pipe design docs into `claude -p --effort high --max-turns 1` for adversarial architecture/security review.
- [filesystem-containment-phase-lessons.md](filesystem-containment-phase-lessons.md) — Evidence-vs-execution distinction, boundary-correction principle, bwrap design, write-probe requirement, Heartgate YAML shape, and 10-step phase-start sequence for filesystem containment phases.
- [governed-canonical-writers.md](governed-canonical-writers.md) — Full governed-writer contract: four writer surfaces (`uacp_state_write`, `uacp_artifact_write`, `uacp_doc_write`, `uacp_config_write`), required context fields, containment rules, Guardian classification, verification pattern, and pitfalls.
- [guardian-hook-audit-pattern.md](guardian-hook-audit-pattern.md) — 7-step hook-audit procedure, single-fire contract (`skip_pre_tool_call_hook` semantics), `_AGENT_LOOP_TOOLS` bypass risk, 4-level risk classification, known safe patterns and pitfalls.
- [guardian-neutral-kernel-adapter.md](guardian-neutral-kernel-adapter.md) — Neutral-kernel→adapter-contract→runtime-plugin→generic-seams principle, 7-step neutralization checklist, 5-item pitfall list. Cross-ref: `docs/runtime/runtime-enforcement.md`.
- [guardian-policy-branch-review-pattern.md](guardian-policy-branch-review-pattern.md) — 6-step pattern for reviewing UACP policy feature branches: isolate change, check defaults, verify containment enforcement, audit test coverage, require feature flag, council recommendation shape.
- [heartgate-council-artifact-management.md](heartgate-council-artifact-management.md) — Phase-local council vs Heartgate Council distinction, retrieval-led reasoning requirement, artifact placement, 6 required Heartgate lenses, runtime/script alignment checklist, session-proven blocker patterns.
- [hermes-adapter-porting-and-cleanup-lessons.md](hermes-adapter-porting-and-cleanup-lessons.md) — UACP adapter ownership direction, hermes_symlink_plugin_probe.py invocation, dirty-state precheck, branch-verification checklist, deferred-action boundary, and stale-gate-task resolution for Hermes porting work.
- [kanban-guard-and-closure-lessons.md](kanban-guard-and-closure-lessons.md) — 7-step closure evidence pattern, workspace-separation boundary, completion metadata field list, completion_blocked_uacp_metadata event, 5-case verification shape, and non-goals for Kanban guard phases.
- [operational-dashboard-and-live-proof.md](operational-dashboard-and-live-proof.md) — Two-surface pattern (dashboard YAML + probe script + proof YAML), 7-item safe-probe checklist, operator approval/authority convention, 3 pitfalls.
- [phase-transition-finalization-lessons.md](phase-transition-finalization-lessons.md) — 9-step finalization sequence, Guardian env-var binding template, PYTHONDONTWRITEBYTECODE/pytest `-c /dev/null` fallbacks, transition-artifact field reminders, operator reporting with explicit non-actions.
- [runtime-adapter-construction-guidelines.md](runtime-adapter-construction-guidelines.md) — Inventory-first, neutral-kernel-must-not-import-host-modules, UACP-leakage anti-pattern, governed writer scope, DB-migration sequencing, do-not-amend-mixed-commits.
- [runtime-trust-boundary-correction-20260514.md](runtime-trust-boundary-correction-20260514.md) — Operator-preference pattern (pause and reframe authority boundary when solution feels fuzzy), 4 out-of-band mutation examples, 3-step correct response. Canonical doctrine: `docs/runtime/runtime-enforcement.md` §Runtime Trust Boundary.
- [skills-validator-alignment-workflow.md](skills-validator-alignment-workflow.md) — 7 trigger categories, 5-phase alignment workflow, validator scope minimum, canonical finding-state list, EDR `not_runtime_active` check, 4 pitfalls.
- [trustless-acp-source-analysis.md](trustless-acp-source-analysis.md) — "What's Universal" 14-pattern table, 6 architectural derivation decisions for UACP, bridge-name reference table (claude/codex/opencode/gemini/kimi). Historical reference only.
