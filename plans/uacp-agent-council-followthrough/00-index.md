# UACP Agent-Council Follow-through Package

Status: active follow-through package  
Created: 2026-05-12T18:04:59.583598+00:00  
Authority root: `UACP_ROOT`  
Scope: preserve and execute the UACP Agent-Council integration context without relying on chat memory.  

---

## Purpose

This package breaks the remaining UACP Agent-Council integration work into numbered context documents, task documents, Kanban import data, and verification/measurement gates.

It exists because a single mega-document cannot preserve the full reasoning context safely across future sessions.

## Numbered documents

1. `01-current-state.md` — what is already done and where the authoritative artifacts live.
2. `02-cognitive-model.md` — the reasoning model: UACP / Agent Council / Kanban / runtimes / tools.
3. `03-open-risks-and-decisions.md` — risks, unresolved decisions, and explicit non-goals.
4. `04-task-breakdown.md` — numbered task graph, dependencies, owners, and acceptance criteria.
5. `05-kanban-delegation.md` — Kanban board/root/child task specification and import manifest.
6. `06-verification-and-measurement-gates.md` — gates, metrics, checks, and pass/warn/block criteria.
7. `07-session-resume-guide.md` — how a future session should resume without chat context.
8. `08-execution-profiles-and-personas.md` — profiles/personas as internal execution configuration, not only external identity.

## Canonical baseline artifacts

- `plans/agent-skills-branch-integration/00-index.md`
- `plans/uacp-skills-and-validator-alignment-phased-plan.md`
- `outputs/agent-skills-integration-current-handoff.md`
- `verification/agent-skills-branch-integration-agent-council-review.yaml`
- `verification/agent-skills-branch-integration-cleanup-verify.yaml`
- `verification/uacp-skills-validator-alignment-verify.yaml`
- `scripts/validate_uacp_artifacts.py`

## Rule for future agents

Do not infer from chat memory. Start here, then read the linked canonical artifacts. If this package and canonical docs/config disagree, canonical docs/config win; then patch this package.

9. `09-current-operating-model-and-future-slots.md` — locked current semi-auto/manual model, rationale, concerns, phase boundaries, and future autonomy slots.

10. `10-execute-task-schema.md` — concrete EXECUTE task schema, runtime/profile boundaries, examples, and completion contract.

11. `11-full-auto-execute-phase-controller.md` — reserved roadmap design target for full-auto EXECUTE phase controller using coordination adapter task graph.

12. `12-current-execution-posture-after-kanban-dogfood.md` — current operational decision to continue remaining UACP design in-session after repeated Kanban worker failures.

13. `13-coordination-adapter-contract.md` — substrate-neutral coordination adapter contract and Hermes Kanban mapping.


14. `14-validator-hardening-and-fixtures.md` — manual-drill validator coverage and fixture guidance.
15. `15-guardian-heartgate-validator-wiring.md` — staged validator-to-Heartgate/Guardian integration design.
16. `16-agent-council-kanban-templates.md` — reusable council-mode Kanban/coordination task templates.
17. `17-runtime-tool-evidence-adapter-manifest.md` — adapter manifest schema and class examples.
18. `18-evidence-domain-registry-selector.md` — Evidence-Domain Registry selector design, explicitly not runtime-active.
19. `19-downstream-agent-skills-extraction.md` — downstream skill extraction plan and drift checks.
