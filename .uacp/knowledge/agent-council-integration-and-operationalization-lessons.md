---
type: analysis
id: agent-council-integration-and-operationalization-lessons
title: Agent Council Integration and Operationalization Lessons
description: Split-plan shape, cognitive-plane anti-patterns, phase-local granularity fields, surface taxonomy, skill/validator propagation, and PLAN→EXECUTE checklist for Agent Council work.
tags: [agent-council, lifecycle, planning, operationalization]
timestamp: 2026-06-17
---

# Agent Council Integration and Operationalization Lessons

Durable lessons for UACP work touching Agent Council integration, council synthesis schemas, orchestration topology, and phase-transition evidence. Drawn from Slice integration work and Phase 6 operationalization (2026-05-15).

Cross-reference `docs/lifecycle/orchestration-model.md` for canonical plane definitions — this doc records lessons and anti-patterns, not plane prose.

---

## Split Planning Package Shape

Do not compress major UACP doctrine or integration work into one giant plan. Produce a split planning package under a directory (e.g. `UACP_ROOT/plans/<topic>/`) with separate files for:

- `00-index.md` — non-negotiables, session-resume guide
- `01-current-state.md` — ground truth
- `02-cognitive-model.md` — (or decisions)
- `03-open-risks-and-decisions.md` — open risks
- `04-task-breakdown.md` — requirements / task breakdown
- `05-kanban-delegation.md` — execution plan / Kanban delegation
- `06-verification-and-measurement-gates.md` — verification gates
- `07-session-resume-guide.md` — context-continuity notes

Keep a compiled reference packet only as a convenience pointer, not the primary review surface. Kanban is coordination memory only: store root/child task IDs, dependencies, allowed files, acceptance criteria, and verification gates. UACP artifacts remain the authority; Kanban tracks execution continuity.

---

## Cognitive-Plane Anti-Patterns

Clarify these layers explicitly when patching UACP. See `docs/lifecycle/orchestration-model.md` for authoritative plane definitions.

Anti-patterns to reject:

- **Kanban-as-thinker** — Kanban records durable tasks, dependencies, status, and handoffs. It is not an agent or decision-maker.
- **Council-as-state-DB** — Agent Council deliberates; it does not store phase state. UACP state lives in `state/current.yaml` and run manifests.
- **Phase-labels-as-deliberation** — Phase labels describe lifecycle position. They do not substitute for deliberative council review.
- **Tools-as-autonomous-authorities** — Tool adapters observe, act, and produce evidence. They do not make governance decisions.
- **Runtime-as-policy** — Runtimes are bounded workers. Guardian/Heartgate enforce boundaries between planes.

---

## Phase-Local Granularity Field Names

Granularity should be phase-local and compositional, not only one intake score. Each phase records:

| Field | Meaning |
|---|---|
| `entry_estimate` | Granularity estimate at phase entry |
| `exit_actual` | Actual granularity score at phase exit |
| `delta_reason` | Explanation of any change from estimate |
| `downstream_projection` | Projected impact on later phases |

Composite run granularity derives from max phase score, cumulative complexity, cross-phase coupling, carried findings/warnings, side effects, and runtime/domain diversity. TRIAGE creates an initial estimate, not final truth. Later phase reassessment can trigger human involvement, tier escalation, or re-plan/checkpoint.

---

## Execution-Surface Taxonomy

Do not call every execution surface a runtime unless it hosts an autonomous agent loop. Canonical taxonomy:

| Label | Examples |
|---|---|
| `agent_runtime` | Hermes, Claude Code, Codex, OpenCode, Kimi, Gemini |
| `tool_adapter` | browser automation, Puppeteer/Playwright, computer use, terminal, OCR, scripts |
| `evidence_service` | Firecrawl, Tavily, SearXNG, web search, scraping APIs, transcripts, domain data providers |
| `control_substrate` | Hermes Kanban |

---

## Skill and Validator Propagation Checklist

When UACP doctrine or config changes, updating docs alone is incomplete if active skills still contain stale assumptions. At minimum, verify:

- lifecycle skills mention phase-local/composite granularity when relevant,
- PLAN/EXECUTE skills preserve the UACP / Agent Council / Kanban cognitive split,
- VERIFY checks canonical finding states and council synthesis artifacts,
- state skills preserve run-manifest fields without letting Kanban become phase state,
- validators catch missing phase-local granularity, invalid finding states, and missing council synthesis fields.

Then create or update lightweight validation scripts when artifact schemas changed.

---

## Surface Inventory Before Patches

Before any council or patch work, create a verification artifact that inventories canonical docs/config/scripts/skills/prior plans and classifies each as:

- `reuse` — no change needed
- `patch` — requires update
- `defer` — out of this scope, record as deferred
- `out_of_scope` — explicitly excluded

This prevents duplicate doctrine and makes EXECUTE bounded. Council prompts should name concrete files/artifacts to inspect. Synthesis artifacts should record `inspected_paths` or equivalent, plus finding evidence with paths. Summary-only council review is not sufficient for runtime/governance correctness claims.

---

## 8 Common Cleanup Items After Doctrine Patches

Check for:

1. Stale council vocabulary in alignment docs (`local council`, `deep council`) — map it to tiers.
2. Phase-transition schema/prose mismatches (`routing_outcome`, `terminal_kind`, disposition names).
3. Undefined `council_synthesis_artifact` schema.
4. Config stubs accidentally described as implemented features.
5. Non-standard finding states — use canonical states like `accepted_risk`.
6. Guardian bypasses under-rated as warnings rather than high accepted risk/blockers.
7. `patch-invalid-transitions-immediately` — if PLAN council discovers a prior transition artifact fails validator/Heartgate policy (invalid enum, missing required `heartgate_coherence`, etc.), patch the transition artifact immediately; do not preserve a known-invalid transition as historical truth.
8. Model routing in canonical doctrine — model routing belongs in operator/runtime config, not canonical doctrine; canonical proposal/docs/config should remain model-agnostic.

---

## Read-Only Syntax Check Trick

`python -m py_compile` may fail under read-only UACP containment because it writes bytecode. Prefer:

```python
PYTHONDONTWRITEBYTECODE=1
ast.parse(source_text)   # read-only syntax check
```

Then run `scripts/validate_uacp_artifacts.py` separately for artifact validation.

---

## PLAN → EXECUTE Verification Checklist

Before PLAN → EXECUTE for Agent Council protocol work:

- [ ] Surface inventory exists and all items classified.
- [ ] PLAN council synthesis exists with `inspected_paths`.
- [ ] Prior transition artifacts pass validator (`scripts/validate_uacp_artifacts.py` returns `RESULT PASS`).
- [ ] Rollback checkpoint and verification command added before transition.
- [ ] Governed writer tool availability confirmed before docs/config mutation.
- [ ] Validator gaps decided explicitly: implement now or record accepted risk with owner and condition.
- [ ] Kanban-backed council automation deferred unless current operating posture explicitly allows it.
- [ ] Skill alignment state documented: in-tree or out-of-tree, when patches land.
- [ ] PLAN → EXECUTE transition carries owned warnings/deferred items and Heartgate coherence where policy requires it.

---

## Retrieval-Led Council and Kept-Artifact Separation

- Phase-local Agent Council synthesis belongs in `verification/` as `kind: uacp.council_synthesis` and is referenced by `council_synthesis_artifact`.
- Heartgate/transition coherence belongs in `heartgate_coherence.artifact_path`.
- Do not collapse them unless the artifact explicitly covers both roles.

---

## Human Involvement Triggers

Human involvement can be selected at TRIAGE or by later phase-local reassessment. Trigger it for:

- Unclear authority.
- Irreversible or external side effects.
- High phase-local or composite granularity.
- Unresolved HIGH/CRITICAL findings.
- Guardian/Heartgate inability to classify a protected action safely.

---

> _Sources: `skills/references/agent-council-integration-lessons.md` (integration lessons) and `skills/references/phase6-agent-council-operationalization-lessons-20260515.md` (2026-05-15 operationalization lessons). Both removed in ADR-0017 / Step 2 Slice 3._
