# Agent-Skills → UACP Integration Current Handoff

Updated: 2026-05-12T18:00:01.043543+00:00

## Current status

The UACP doctrine/config/skills alignment pass is complete and verified.

Completed:

- Split planning package created under `plans/agent-skills-branch-integration/`.
- Canonical docs/config patched for:
  - Agent Council as deliberative orchestration,
  - Kanban as coordination memory,
  - UACP as governance cognition,
  - phase-local + composite granularity,
  - human involvement from TRIAGE and phase reassessment,
  - runtime/tool/evidence adapter distinction,
  - council synthesis schema,
  - Evidence-Domain Registry seed status.
- Local Agent Council review completed:
  - `verification/agent-skills-branch-integration-agent-council-review.yaml`
- Cleanup verification completed:
  - `verification/agent-skills-branch-integration-cleanup-verify.yaml`
- Lifecycle skills patched under `HERMES_ROOT/skills/devops/uacp/`.
- Lightweight validator created:
  - `scripts/validate_uacp_artifacts.py`
- Skills/validator verification passed:
  - `verification/uacp-skills-validator-alignment-verify.yaml`

## Current mental model

```text
UACP = governance cognition
Agent Council = deliberative orchestration
Kanban = coordination memory
Runtimes = bounded worker cognition / execution loops
Tools + evidence services = actuation / observation
Guardian + Heartgate = boundary enforcement
```

## Do we need Kanban now?

Recommended: yes, for the remaining implementation/runtime work.

Reason: the remaining work is now a multi-phase backlog likely to outlive this chat context. Kanban should not be used as UACP phase state, but it is useful as durable coordination memory for task graph, dependencies, ownership, status, and handoffs.

Do not use Kanban for already-finished doc/skill patches unless tracking history is needed. Use Kanban for the deferred implementation backlog below.

## Suggested Kanban root task

Title: `UACP Agent-Council Integration — Runtime/Validator Follow-through`

Description:

- Authority artifact: `plans/uacp-skills-and-validator-alignment-phased-plan.md`
- Current handoff: `outputs/agent-skills-integration-current-handoff.md`
- Verification baseline: `verification/uacp-skills-validator-alignment-verify.yaml`
- Goal: convert stabilized doctrine/skill alignment into durable runtime/tooling implementation without losing context.

## Suggested child tasks

1. `validator-hardening`
   - Expand `scripts/validate_uacp_artifacts.py` into stricter schema validation or JSON Schema if needed.
   - Add tests or sample fixtures.
   - Acceptance: validator catches missing phase-local granularity, invalid finding states, missing council fields.

2. `guardian-heartgate-validator-wiring`
   - Decide where the validator is invoked: Guardian, Heartgate, lifecycle skills, or manual CLI only.
   - Acceptance: bounded design doc names exact integration point and failure mode.

3. `agent-council-kanban-templates`
   - Create Kanban task templates for Agent Council execution topology.
   - Include council mode, tier, roles, dispatch surfaces, side-effect boundaries, expected artifact.
   - Acceptance: a future UACP PLAN can generate Kanban tasks without relying on chat context.

4. `runtime-tool-evidence-adapter-manifest`
   - Define manifest shape for agent runtimes, tool adapters, and evidence services.
   - Include examples: Hermes, Claude Code, Codex, browser/computer-use, Firecrawl, Tavily, SearXNG.
   - Acceptance: configs distinguish runtime vs tool vs evidence service.

5. `evidence-domain-registry-selector`
   - Implement or design runtime selector for Evidence-Domain Registry.
   - Acceptance: `implementation_status` can move from `not_runtime_active` only after selector exists and is verified.

6. `downstream-agent-skills-extraction`
   - Re-extract agent-skills from stabilized UACP doctrine.
   - Acceptance: downstream skills implement UACP and do not redefine it.

## Next recommended action

Create a Kanban root task and child tasks from the above backlog. If Kanban tooling is unavailable in the current session, use this handoff file as the durable source of truth until a Kanban board/task graph is created.
