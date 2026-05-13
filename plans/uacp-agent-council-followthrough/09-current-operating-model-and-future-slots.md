# 09 — Current Operating Model And Future Autonomy Slots

Status: active decision record  
Created: 2026-05-12T19:09:15.903556+00:00  
Scope: UACP orchestration, delegation, profiles, Agent Council, Kanban/coordination adapter, and future full-autonomy topology.

---

## 1. Decision summary

For the current stage, UACP will operate in **manual / semi-automatic orchestration mode**.

Canonical current-stage rule:

```text
TRIAGE / PROPOSE / PLAN / VERIFY / RESOLVE:
  default: main orchestrator
  optional: delegate_task same-profile branches
  optional: external runtime when justified
  no Kanban by default

EXECUTE:
  default for non-trivial work: Kanban / coordination adapter
  workers: Hermes profile workers, native subagents, external runtimes, tools, or humans as selected per task
```

Kanban is used primarily in EXECUTE because that is where durable ownership, dependencies, allowed-file boundaries, retries, timeouts, progress tracking, and worker dispatch matter most.

The workflow phases before and after EXECUTE should remain lighter unless the phase itself becomes long-running, multi-worker, profile-specific, or fully autonomous.

---

## 2. Rationale and intent

The original risk was that Agent Council and UACP execution were drifting toward being tightly coupled to Hermes Kanban. That would make Hermes Kanban a hidden execution doctrine and create vendor/runtime lock-in.

The intent is to preserve UACP as the authority layer while keeping execution surfaces replaceable.

Correct separation:

```text
UACP = governance, phase, authority, risk, evidence obligations
Insight / phase controller = topology decision for the phase
Agent Council = adaptive deliberation protocol
Coordination adapter = task/comment/artifact persistence and dispatch
Worker runtime = actual executor/analyser/reviewer
UACP artifacts/state = canonical evidence and decisions
```

Hermes Kanban is the current coordination adapter for durable EXECUTE work. It is not UACP doctrine and not the Agent Council substrate.

---

## 3. Questions and concerns captured

### Q1 — Does every phase need Kanban?

No.

Only EXECUTE commonly needs Kanban or another durable coordination adapter. TRIAGE, PROPOSE, PLAN, VERIFY, and RESOLVE usually do not need it in manual/semi-auto mode.

Those phases can use:

- main orchestrator reasoning,
- `delegate_task` same-profile scratch branches,
- external runtimes when justified,
- direct artifacts.

They should use coordination only when the phase itself needs durable multi-worker state or full-autonomy command-bot control.

### Q2 — Is `delegate_task` equivalent to a profile worker?

No.

`delegate_task` is a same-profile, in-process branch. It can use a focused prompt, restricted tools, and in some cases model/provider overrides, but it does not load a separate Hermes profile home, profile-local doctrine stack, profile-local memory, or profile-local skills.

Therefore:

```text
delegate_task = quick same-profile branch
profile worker = Kanban/spawned Hermes profile process
external runtime = Claude Code / Codex / OpenCode / Kimi / etc.
```

### Q3 — Why have `uacp-planner` / `uacp-verifier` profiles if we are not full-auto yet?

In the current stage, named UACP profiles are **role templates and future topology slots**, not mandatory live workers.

Use the planner/verifier/devil's-advocate roles directly through the main orchestrator or same-profile scratch branches unless durable profile-specific work is justified.

Named profiles become active workers only when:

- profile-specific prompt/model/tool policy matters,
- async/durable execution is needed,
- formal Profile Council is selected,
- full-autonomous topology is implemented later.

### Q4 — Can Kanban host debate/review?

Yes, but Kanban does not debate.

Kanban can coordinate debate/review by storing tasks, comments, artifacts, dependencies, and statuses. The actual debate requires an active coordinator/orchestrator loop plus assigned worker runtimes.

Passive task completion is not enough for adaptive debate. Reruns, regrouping, role changes, and escalation require an active council/phase controller.

### Q5 — Is Agent Council now Kanban-locked?

No. It must not be.

Agent Council is an adaptive deliberation protocol. Kanban is only one coordination adapter.

Future coordination adapters may include a custom UACP command bot queue, Linear, GitHub Issues, Notion, SQLite event log, Temporal-style workflow engine, or other systems.

---

## 4. Current-stage operating model

### TRIAGE

Default executor: main orchestrator.

Allowed helpers:

- `delegate_task` for quick classification/ambiguity checks,
- external runtime only if unusual domain/runtime evidence is required.

Kanban: no, unless intake itself becomes durable/multi-party.

### PROPOSE

Default executor: main orchestrator.

Allowed helpers:

- `delegate_task` for quick challenge or alternative framing,
- external runtime for independent critique when proposal risk/ambiguity justifies it.

Kanban: no by default.

### PLAN

Default executor: main orchestrator.

Allowed helpers:

- `delegate_task` for alternate decomposition, missing-dependency checks, and risk critique,
- external runtime for architecture/runtime-specific second opinion.

Kanban: no by default. Use only if planning itself becomes a durable multi-role project.

### EXECUTE

Default for non-trivial work: Kanban / coordination adapter.

Each EXECUTE Kanban task is a bounded work unit, not necessarily a whole UACP phase. A task may represent a sub-phase or execution slice with its own local plan/execute/verify loop.

Each task may be handled by:

- a Hermes profile worker,
- same-profile branch/delegate subagents inside that worker,
- an external runtime adapter,
- a tool/evidence adapter,
- a human checkpoint.

Each task must declare:

- objective,
- allowed files/surfaces,
- forbidden files/surfaces,
- side effects,
- runtime/profile choice where relevant,
- verification expectations,
- output/evidence contract,
- rollback/escape path when relevant.

### VERIFY

Default executor: main orchestrator.

Allowed helpers:

- `delegate_task` for provisional second checks,
- external runtime for independent verification,
- profile/Kanban workers only for long-running, multi-role, cross-runtime, evidence-heavy, or finding-driven verification.

Kanban: no by default.

### RESOLVE

Default executor: main orchestrator.

Allowed helpers:

- `delegate_task` for lesson extraction or wording alternatives,
- direct memory/skill decisions as appropriate.

Kanban: only for durable follow-up tasks.

---

## 5. Current-stage routing rules

### Use main orchestrator when

- the phase can complete synchronously,
- one artifact is enough,
- risk is low/moderate and evidence is clear,
- no durable worker ownership is required.

### Use `delegate_task` when

- a same-profile scratch branch helps thinking,
- quick brainstorming/critique/research/file inspection is enough,
- no true profile isolation is needed,
- the result is provisional and synchronous.

### Use external runtime when

- model/runtime/toolchain diversity materially improves confidence,
- heavy coding/debugging/refactor is needed,
- independent perspective is required,
- a distinct coding-agent environment is beneficial.

### Use Kanban / coordination adapter when

- EXECUTE work is non-trivial,
- durable task ownership is needed,
- dependencies/retries/timeouts matter,
- profile-specific workers are needed,
- work must continue beyond the current chat turn,
- output must be auditable across worker units,
- external runtimes need coordination.

---

## 6. Important clarification: Kanban task vs phase

A Kanban task should not be defined as exactly equal to a UACP lifecycle phase.

Better rule:

```text
UACP phase = lifecycle envelope
Kanban task = bounded work unit inside a phase, most often EXECUTE
```

In EXECUTE, each Kanban task may contain a local mini-cycle:

```text
understand task -> implement/analyse -> self-check -> report evidence
```

For future full automation, command-bot/controller tasks may represent phase controllers, but that is a future topology, not the current manual/semi-auto default.

---

## 7. Future extensions and reserved slots

### Reserved slot A — Full autonomous topology

Future design may introduce command-bot / phase-controller tasks:

```text
uacp-triage-controller
uacp-propose-controller
uacp-plan-controller
uacp-execute-controller
uacp-verify-controller
uacp-resolve-controller
```

These controllers would manage phase-specific topology, timeouts, worker selection, reruns, evidence checks, and transitions.

Not implemented now.

### Reserved slot B — Profile Council

Named profiles remain future execution identities:

```text
uacp-planner
uacp-verifier
uacp-devils-advocate
uacp-integrator-critic
uacp-safety-privacy-reviewer
uacp-evidence-researcher
```

Current use: role templates and optional async escalation targets.

Future use: actual profile workers selected by phase controllers or Agent Council.

### Reserved slot C — Coordination adapter interface

Hermes Kanban should be replaceable by other coordination substrates.

Adapter contract:

```yaml
create_unit: required
assign_unit: required
declare_dependencies: required
attach_context: required
attach_artifact_or_comment: required
read_unit_outputs: required
mark_state: required
retry_or_rerun_unit: required
preserve_provenance: required
watch_or_poll_state: optional
notify: optional
```

### Reserved slot D — Adaptive Agent Council coordinator

Agent Council needs an active coordinator capable of:

- selecting roles,
- starting rounds,
- reading outputs,
- detecting weak evidence,
- rerunning or regrouping roles,
- escalating from scratch council to profile council,
- escalating to cross-runtime council,
- deciding synthesis readiness,
- recording termination rationale.

### Reserved slot E — Dispersed multi-agent review/audit

For full-dimensional, full-perspective review and audit, UACP should eventually support dispersed multi-agent councils:

- role diversity,
- profile diversity,
- model diversity,
- runtime diversity,
- tool/evidence diversity,
- human checkpoint where authority/risk requires it.

This should be used selectively for high-risk, high-ambiguity, cross-domain, security/privacy/legal/financial/safety, or major architecture/execution decisions.

---

## 8. Action plan

### Phase 1 — Lock current semi-auto/manual doctrine

- Treat current workflow phases as main-orchestrator-led.
- Use `delegate_task` and external runtimes only as helpers outside EXECUTE.
- Use Kanban mainly for non-trivial EXECUTE.
- Keep named UACP profiles as role templates/future slots unless async profile work is explicitly justified.

### Phase 2 — Tighten execution-task schema

Define the required EXECUTE Kanban task shape:

- objective,
- allowed files/surfaces,
- forbidden files/surfaces,
- selected runtime/profile,
- side effects,
- evidence output,
- verification command/check,
- rollback note,
- completion contract.

### Phase 3 — Design coordination adapter contract

Extract a substrate-neutral adapter spec so Hermes Kanban remains replaceable.

### Phase 4 — Design adaptive council coordinator

Define the coordinator loop for scratch/profile/cross-runtime councils:

- round state,
- role selection,
- rerun/regroup triggers,
- escalation triggers,
- synthesis readiness,
- termination rationale.

### Phase 5 — Reserve but defer full autonomous topology

Document command-bot/phase-controller topology, but do not implement until semi-auto execution is stable.

### Phase 6 — Later: dispersed multi-agent audit

Design a higher-tier review/audit mode only after the coordination adapter and council coordinator are stable.

---

## 9. Locked current doctrine statement

Until explicitly superseded:

```text
UACP current mode is manual/semi-auto.
Kanban is used primarily for non-trivial EXECUTE.
TRIAGE, PROPOSE, PLAN, VERIFY, and RESOLVE remain orchestrator-led unless phase-local needs justify delegation, external runtime, or durable coordination.
delegate_task is a same-profile scratch branch, not a profile worker.
Named UACP profiles are role templates and optional/future execution identities.
Hermes Kanban is a replaceable coordination adapter, not Agent Council doctrine.
Agent Council is an adaptive deliberation protocol that may use delegate branches, profile workers, external runtimes, humans, and coordination adapters as selected by phase-local topology.
```


## Roadmap addition — Full-auto EXECUTE phase controller

Add a bounded prototype for full-auto `EXECUTE` phase execution through a phase controller plus Kanban/coordination-adapter task graph. Expected artifact: `11-full-auto-execute-phase-controller.md`. This comes before full lifecycle autonomy.


## 10. Current execution posture after Kanban dogfood

After repeated default-profile Kanban worker crashes/protocol violations during UACP design dogfood, remaining UACP reramp design work should continue primarily in the main session, with `delegate_task` used for bounded same-profile critique when useful. Kanban remains the target EXECUTE coordination adapter, but further UACP design dogfood through Kanban should pause until the worker reliability issue is diagnosed. See `12-current-execution-posture-after-kanban-dogfood.md`.
