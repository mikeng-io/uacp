# UACP Agent-Council Follow-through — Execution Plan

Status: approved-for-execution  
Run: `uacp-agent-council-followthrough-20260513`  
Authority: `proposals/uacp-agent-council-followthrough-20260513.yaml`  
Triage: `state/runs/uacp-agent-council-followthrough-20260513-triage.yaml`

## Execution topology

- Main orchestrator owns TRIAGE, PROPOSE, PLAN, EXECUTE synthesis, VERIFY, and RESOLVE.
- `delegate_task` uses the temporary GPT-5.4-mini delegation configuration for bounded critique/research only.
- Kanban worker dogfood remains paused for UACP design work because `12-current-execution-posture-after-kanban-dogfood.md` recorded worker crash/protocol reliability issues.
- External runtime is reserved for heavy code/runtime debugging only; not selected for this documentation/validator pass.

## Work units

1. T1 Validator hardening
   - Patch `scripts/validate_uacp_artifacts.py` to validate gate-selection artifacts, execute-task surfaces, evidence clusters, finding states, council artifacts, and phase transitions.
   - Add sample fixture guidance in `14-validator-hardening-and-fixtures.md`.
2. T2 Guardian/Heartgate validator wiring design
   - Create `15-guardian-heartgate-validator-wiring.md`.
3. T3 Agent Council to Kanban task templates
   - Create `16-agent-council-kanban-templates.md`.
4. T4 Runtime/tool/evidence adapter manifest
   - Create `17-runtime-tool-evidence-adapter-manifest.md`.
5. T5 Evidence-Domain Registry selector design
   - Create `18-evidence-domain-registry-selector.md`.
6. T6 Downstream agent-skills extraction plan
   - Create `19-downstream-agent-skills-extraction.md`.
7. T7 Final verification and Agent Council
   - Run validator, bounded council review, write council synthesis, verification, RESOLVE, and lesson artifacts.

## Write containment

Allowed:
- `scripts/validate_uacp_artifacts.py`
- `plans/uacp-agent-council-followthrough/*.md`
- `proposals/uacp-agent-council-followthrough-20260513*.yaml`
- `plans/uacp-agent-council-followthrough-20260513-execution-plan.md`
- `executions/uacp-agent-council-followthrough-20260513.yaml`
- `verification/uacp-agent-council-followthrough-20260513*.yaml`
- `outputs/uacp-agent-council-followthrough-20260513*.yaml`
- `knowledge/lessons/uacp-agent-council-followthrough-20260513.yaml`
- `state/runs/uacp-agent-council-followthrough-20260513*.yaml`

Forbidden:
- `PRIVATE_ROOT`
- public/external posting surfaces
- unrelated Hermes config/model routing changes
- production Guardian/Heartgate runtime implementation beyond design artifacts

## Verification

Required:
- YAML parse/validator pass over all run artifacts.
- Explicit finding states from canonical set: `open`, `resolved`, `accepted_risk`, `not_applicable`, `deferred`.
- Final Agent Council synthesis across document authority, state traceability, Kanban boundary, runtime enforcement, adapter taxonomy, evidence registry, downstream extraction, and operational feasibility.

## Phase-local granularity

- PLAN entry estimate: 8
- PLAN exit actual: 8
- Downstream projection: EXECUTE 8, VERIFY 8, RESOLVE 6

## Human involvement

Not required for local reversible artifacts. Required if production runtime enforcement, public side effects, or unresolved CRITICAL findings appear.
