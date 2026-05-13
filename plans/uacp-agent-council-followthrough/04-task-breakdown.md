# 04 — Task Breakdown

Status: active follow-through package  
Created: 2026-05-12T18:04:59.583598+00:00  
Authority root: `UACP_ROOT`  
Scope: preserve and execute the UACP Agent-Council integration context without relying on chat memory.  

---

## Task graph overview

Root task: `UACP Agent-Council Integration — Runtime/Validator Follow-through`

### T1 — Validator hardening

Objective: Improve `scripts/validate_uacp_artifacts.py` from lightweight sanity checker to a more reliable manual-drill validator.

Dependencies: none.

Inputs:

- `config/phase-transitions.yaml`
- `config/review-routing.yaml`
- `config/evidence-clusters.yaml`
- current verification artifacts

Acceptance:

- catches missing `phase_local_granularity`, `composite_granularity`, `human_involvement` in phase transitions,
- catches invalid finding states,
- catches missing council synthesis required fields,
- has sample pass/fail fixtures or documented sample commands.

### T2 — Guardian/Heartgate validator wiring design

Objective: Decide where validator logic belongs in runtime enforcement.

Dependencies: T1 can run in parallel, but final design should account for T1 output.

Acceptance:

- design states whether validator remains CLI/manual or plugs into Guardian/Heartgate,
- names exact integration point,
- names fail-open/fail-closed behavior,
- names how bypass risks are recorded.

### T3 — Agent Council → Kanban task templates

Objective: Create reusable task templates for council-mode execution on Kanban.

Dependencies: none.

Acceptance:

- templates include council mode, tier, roles, phase-local granularity, dispatch surfaces, authority, side effects, expected artifact, verification gates,
- examples cover `execute`, `verify`, and `audit` modes,
- Kanban is represented as coordination memory only.

### T4 — Runtime/tool/evidence adapter manifest

Objective: Define manifest shape for agent runtimes, tool adapters, evidence services, and control substrates.

Dependencies: none.

Acceptance:

- manifest distinguishes `agent_runtime`, `tool_adapter`, `evidence_service`, `control_substrate`,
- examples include Hermes, Claude Code, Codex, browser/computer-use, Firecrawl, Tavily, SearXNG,
- manifest includes authority/side-effect/provenance/audit classification.

### T5 — Evidence-Domain Registry selector design/implementation

Objective: Convert Evidence-Domain Registry from seed target toward runtime selector.

Dependencies: T4 recommended.

Acceptance:

- selector design maps phase/artifact/risk/domain/runtime context to clusters, roles, and verification requirements,
- `implementation_status` remains `not_runtime_active` until selector is implemented and verified,
- tests/examples show at least software, governance, research, and infra selection.

### T6 — Downstream agent-skills extraction plan

Objective: Plan extraction from stabilized UACP into downstream agent-skills without parallel doctrine.

Dependencies: T1–T5 recommended, but can begin as design only.

Acceptance:

- maps UACP docs/config to downstream skills,
- identifies deprecated deep-* wrappers and compatibility aliases,
- defines tests/checks for drift against UACP doctrine.

### T7 — Final council review and RESOLVE

Objective: Run local Agent Council or deeper council after tasks complete, then resolve.

Dependencies: T1–T6.

Acceptance:

- council report exists,
- unresolved HIGH/CRITICAL findings are resolved, accepted, or re-planned,
- final verification artifact exists,
- RESOLVE artifact states memory/skill/doc follow-up decisions.


### T8 — Execution profile/persona matrix

Objective: Design how UACP Agent Council roles map to Hermes profiles or other runtime execution personas.

Dependencies: T4 recommended because profile selection depends on runtime/tool/evidence adapter taxonomy.

Acceptance:

- defines role vs profile distinction,
- proposes profile matrix for planner, implementer, verifier, Devil's Advocate, Integrator Critic, evidence researcher, and adapter specialist,
- specifies model/provider/reasoning/tool/workdir dimensions,
- states whether to create actual Hermes profiles now or keep as design,
- confirms profile-local prompts are downstream of UACP canonical docs/config.


### T9 — Lock current operating model and future slots

Objective: Preserve the agreed manual/semi-auto orchestration boundary and reserve future full-autonomy topology without prematurely implementing it.

Acceptance:

- current mode is manual/semi-auto,
- Kanban/coordination is primary for non-trivial EXECUTE only,
- non-EXECUTE phases default to main orchestrator with delegate_task/external runtime helpers,
- delegate_task is documented as same-profile branch,
- named UACP profiles are role templates/future slots unless async profile-specific work is justified,
- future full-autonomy and dispersed multi-agent audit slots are recorded.



### T10 — EXECUTE task schema and examples

Objective: Define the concrete schema and examples for bounded UACP EXECUTE work units.

Dependencies: T9 / current operating model should be locked first.

Acceptance:

- defines required and optional EXECUTE task fields,
- distinguishes UACP phase from bounded work unit,
- maps runtime surfaces: delegate_task, Hermes profile worker, external runtime, tool/evidence adapter, human checkpoint,
- includes completion/evidence contract,
- includes adapter-neutral Kanban mapping,
- includes examples for docs/config, code implementation, verification, external runtime, and human checkpoint tasks.

### T11 — Full-auto EXECUTE phase controller design

Objective: Design the bounded full-auto `EXECUTE` phase controller for the current UACP reramp.

Dependencies: T10 / `10-execute-task-schema.md` should be reviewed first.

Acceptance:

- limits full-auto scope to EXECUTE phase only,
- uses `10-execute-task-schema.md` for worker task generation,
- treats Hermes Kanban as current coordination adapter, not doctrine,
- defines controller loop for create/assign/monitor/read/rerun/escalate/close,
- handles worker crash, timeout, blocked, and protocol-violation states,
- writes EXECUTE evidence artifact and pass/warn/block readiness for VERIFY,
- reserves but does not implement full lifecycle autonomy.


### T12 — Current execution posture after Kanban dogfood

Objective: Record the operational decision to continue remaining UACP reramp design work in-session after repeated default-profile Kanban worker failures.

Acceptance:

- records observed Kanban worker crash/protocol failures,
- states main session is primary executor for remaining design/docs/config work,
- keeps delegate_task as optional same-profile scratch critique,
- pauses further UACP design dogfood through Kanban workers until worker reliability is diagnosed,
- preserves Kanban as target EXECUTE coordination adapter, not removed architecture.


### T13 — Coordination adapter contract

Objective: Define the substrate-neutral coordination adapter contract so Hermes Kanban remains replaceable.

Dependencies: T10 and T11 recommended.

Acceptance:

- defines adapter purpose and non-goals,
- specifies required operations and data objects,
- maps Hermes Kanban to the contract,
- states portability requirements for future custom queues/issue trackers/workflow engines,
- defines failure/provenance semantics for controller use,
- clarifies what remains UACP-owned versus adapter-owned.
