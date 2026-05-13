# 08 — Execution Profiles And Personas

Status: active follow-through design note  
Created: 2026-05-12T18:23:47.715580+00:00  

---

## Question

Should UACP use Hermes profiles / execution personas like Claude Code or Codex agent definitions, where each agent can have different prompts, models, reasoning levels, tools, and working directories?

## Answer

Yes. Profiles should be part of the UACP execution design.

They are not only external/public representation. They can also be internal execution personas used by Agent Council and Kanban workers.

## Conceptual distinction

```text
Agent Council role = cognitive responsibility
Hermes profile = concrete runtime configuration
```

A role says what kind of thinking is needed:

- planner,
- implementer,
- verifier,
- Devil's Advocate,
- Integrator Critic,
- evidence researcher,
- safety/privacy reviewer,
- adapter specialist.

A profile says how that role runs:

- model/provider/fallback chain,
- reasoning effort,
- tools enabled,
- permissions,
- profile-local instruction stack,
- working directory/project context,
- memory/session isolation.

## Why this matters for UACP

UACP should not rely on an accidental default worker for all council tasks.

For durable execution, PLAN should specify:

- which roles are needed,
- which profiles are allowed/preferred for those roles,
- what model/reasoning/tool differences matter,
- when profile diversity is required for verification confidence,
- when a cheaper/default profile is sufficient.

## Profile-local instruction directories

Hermes profiles can have isolated config/session/skills/memory. They can also load project/context files from a custom workdir. This allows deeper instruction prompts for UACP roles.

Examples:

- `uacp-planner` — stronger planning instructions, medium/high reasoning, docs/config tool scope.
- `uacp-implementer` — implementation prompt, file/terminal scope, test discipline.
- `uacp-verifier` — adversarial verification prompt, read-heavy scope.
- `uacp-devils-advocate` — challenge assumptions, no write by default.
- `uacp-evidence-researcher` — web/evidence tools, no state mutation.

## Authority rule

Profile instructions are downstream implementation. They must not override UACP canonical docs/config.

If a profile prompt conflicts with UACP, UACP wins.

## Design task needed

Create a profile/role matrix and decide whether to implement actual Hermes profiles now or keep the mapping as design until the runtime adapter manifest is complete.


---

## Dispatch surface choice: subagent profile vs external runtime

UACP should treat profile selection and runtime selection as two separate decisions.

```text
role = cognitive job
profile = Hermes execution identity/configuration
runtime surface = where the work actually runs
```

A profile is not itself the runtime boundary. It is the stable pre-run configuration for a worker. That worker may then:

1. execute directly as a Hermes worker,
2. call native `delegate_task` for bounded internal subagents,
3. dispatch a durable Hermes Kanban task to another profile,
4. invoke an external runtime adapter such as Claude Code, Codex, OpenCode, or Kimi Code when escalation is justified.

The selection order should be:

1. **Select role** — what cognitive responsibility is needed?
2. **Select profile** — what prompt/model/tool/permission bundle should represent that role?
3. **Select runtime surface** — should the selected profile do the work directly, delegate internally, spawn/assign another Hermes profile, or call an external coding/runtime agent?
4. **Record evidence** — capture profile, runtime, tool boundary, fallback chain, side effects, and verification expectation in task metadata or council synthesis.

### Current Hermes capability boundary

Current native `delegate_task` children are in-process subagents. They can receive:

- task goal/context,
- restricted toolsets,
- leaf/orchestrator role,
- per-call ACP transport override,
- inherited or delegation-configured model/provider/reasoning settings.

They do **not** currently instantiate a separate Hermes `--profile` home. They inherit the parent process and use an ephemeral child prompt with `skip_memory=True` and `skip_context_files=True`.

Therefore:

- Use `delegate_task` for short bounded internal analysis/research/light edits.
- Use Hermes Kanban assignment or a spawned `hermes --profile <name>` process when the task truly needs a full profile with isolated config, skills, memory/session, gateway identity, or stable model/tool policy.
- Use an external runtime adapter only when scale, complexity, runtime need, independent perspective, verification confidence, or execution durability justifies escalation.

### Routing matrix

| Need | Preferred surface | Reason |
|---|---|---|
| Quick bounded reasoning, drafting, critique, file inspection | Native `delegate_task` | Low overhead; parent waits; simple evidence surface. |
| Stable role persona/model/tool policy but still Hermes-native | Hermes profile via Kanban worker or spawned `hermes --profile` | Full profile config, isolated memory/session/config, durable task ownership. |
| Multiple durable work units with dependencies | Hermes Kanban assigned to profiles | Coordination memory and profile-based worker dispatch. |
| Heavy repo implementation, refactor, debugging, long coding loop | External coding runtime, optionally launched by a Hermes profile adapter | Dedicated runtime/toolchain and stronger autonomous coding behavior. |
| Independent critique / second model perspective | External runtime or model-diverse Hermes profile | Confidence comes from independence, not just another prompt. |
| Sensitive/governed mutation | Profile with least-permission tools, Guardian/Heartgate checkpoint, possible human approval | Permissions and side effects matter more than convenience. |

### Profile-mediated external delegation

A UACP profile may act as an adapter-controller for an external runtime.

Example:

```text
uacp-code-adapter-claude
  role: external coding adapter/controller
  Hermes profile config: limited terminal/file/kanban tools
  runtime action: invoke Claude Code only for approved coding units
  obligation: wrap Claude output in UACP evidence/finding format
```

This is different from simply using Claude Code directly. The profile-mediated pattern is useful when UACP needs:

- consistent preflight checks,
- profile-specific authority constraints,
- task metadata propagation,
- evidence normalization,
- stable fallback from one external runtime to another.

For ordinary heavy coding, direct external runtime dispatch from the orchestrator is acceptable if the UACP artifact records the reason and evidence contract. Profile mediation is preferred when the adapter behavior itself should be stable, reusable, or least-privilege.

## Proposed UACP profile set

Naming convention: `uacp-<function>` for internal governance workers, and `uacp-adapter-<runtime>` for profiles whose main job is to operate an external runtime.

### Core governance profiles

#### `uacp-orchestrator`

Positioning: Main UACP execution-topology designer and synthesis owner.

Use when:

- choosing council tier,
- assigning Kanban/profile work,
- combining worker outputs,
- deciding escalation or human checkpoint needs.

Configuration needs:

- model: high-reliability default model with full fallback chain,
- reasoning: medium/high,
- tools: skills, file/read, search, session_search, kanban, delegation, terminal only for safe inspection,
- memory: enabled only for durable operator/project preferences; avoid task-progress memory,
- workdir: `UACP_ROOT` or current governed workspace,
- write permission: docs/config/state only under declared UACP authority.

#### `uacp-planner`

Positioning: Converts approved scope into phased execution graph.

Use when:

- decomposing work,
- designing rollback/evidence strategy,
- estimating phase-local granularity,
- selecting profile/runtime matrix.

Configuration needs:

- model: strong planning model; fallback GPT → MiniMax → other configured chain,
- reasoning: high for complex plans,
- tools: file/read/write for plans, kanban, skills, limited search,
- workdir: governed repo or `UACP_ROOT`,
- default side effects: write planning artifacts only.

#### `uacp-implementer`

Positioning: Bounded execution worker for local doc/config/code changes.

Use when:

- implementing one Kanban task,
- editing declared files,
- running local verification commands.

Configuration needs:

- model: coding-capable model; can be cheaper than orchestrator if task is narrow,
- reasoning: medium,
- tools: file, terminal, search_files, patch, optional web only when declared,
- checkpoints: enabled where supported,
- workdir: target repo/worktree,
- write permission: only allowed_files from task metadata.

#### `uacp-verifier`

Positioning: Evidence checker and finding writer.

Use when:

- checking outputs against acceptance criteria,
- validating YAML/schema/tests,
- producing pass/warn/block artifacts.

Configuration needs:

- model: high precision, may differ from implementer for independence,
- reasoning: medium/high,
- tools: read-heavy file/search/terminal; write only verification artifacts,
- workdir: target repo/UACP root,
- default side effects: no source mutation unless explicitly assigned remediation.

#### `uacp-devils-advocate`

Positioning: Adversarial challenge profile.

Use when:

- surfacing hidden assumptions,
- checking policy loopholes,
- challenging execution topology,
- looking for high-impact failure modes.

Configuration needs:

- model: independent from planner/implementer when possible,
- reasoning: high,
- tools: read/search only by default,
- write permission: findings/comments only,
- prompt: actively argue against the proposal without becoming obstructionist.

#### `uacp-integrator-critic`

Positioning: Coherence and downstream-integration reviewer.

Use when:

- multiple workers changed related artifacts,
- docs/config/skills must stay aligned,
- outputs need synthesis before VERIFY/RESOLVE.

Configuration needs:

- model: strong synthesis model,
- reasoning: high,
- tools: read/search, limited file write for synthesis artifacts,
- focus: authority chain, naming, schema consistency, downstream skill extraction.

#### `uacp-evidence-researcher`

Positioning: Grounding and external information gatherer.

Use when:

- sources, docs, APIs, prices, papers, or external facts matter,
- evidence clusters need source citations.

Configuration needs:

- model: cost-efficient research model with good summarization,
- reasoning: medium,
- tools: web/search/browser/extraction, file write only to evidence artifacts,
- no authority to mutate governed source artifacts.

#### `uacp-safety-privacy-reviewer`

Positioning: Sensitive-data, side-effect, trust-boundary reviewer.

Use when:

- private data, credentials, public posting, payments, external APIs, or user-visible side effects are involved.

Configuration needs:

- model: cautious/high-precision,
- reasoning: high,
- tools: read/search only unless explicitly approved,
- strict `/private` and secret-handling boundaries,
- output: blocker/warning findings with mitigation.

### External adapter profiles

#### `uacp-adapter-claude-code`

Positioning: Hermes profile that operates Claude Code as an external runtime adapter.

Use when:

- heavy coding or refactor benefits from Claude Code,
- UACP wants stable preflight/evidence wrapping around Claude Code.

Configuration needs:

- model: economical Hermes controller model is acceptable; Claude Code is the substantive coding runtime,
- tools: terminal, file/read, kanban; no broad messaging/memory side effects,
- prompt: state one-sentence escalation reason before invoking Claude Code,
- evidence: capture command/session id, changed files, tests, and findings.

#### `uacp-adapter-codex`

Positioning: Hermes profile that operates Codex as an external runtime adapter.

Use when:

- Codex runtime/model is preferred for implementation/review,
- independent OpenAI-family coding perspective is wanted.

Configuration needs:

- model: controller model can be default/minimal; Codex does execution,
- tools: terminal or MCP Codex interface, file/read, kanban,
- evidence: thread id, summary, diff/test results, unresolved risks.

#### `uacp-adapter-opencode` / `uacp-adapter-kimi`

Positioning: Alternative external coding-runtime adapter profiles.

Use when:

- provider quota/cost/toolchain favors those runtimes,
- an independent runtime family improves verification confidence.

Configuration needs:

- same adapter-controller shape as above,
- runtime-specific auth/CLI readiness checks,
- normalized UACP evidence output.

## Can delegated tasks use different profiles?

Design answer: yes, UACP should support this.

Current implementation nuance:

- Native `delegate_task` supports different model/provider/toolsets/ACP transport, but not full separate Hermes profiles.
- Durable Hermes Kanban workers can be assigned to profile names and are the preferred current mechanism for profile-specific delegated work.
- A manually spawned process can run `hermes --profile <name> chat -q ...` when a one-off full-profile worker is needed.
- External runtime delegation is a separate adapter choice, not the same thing as a native Hermes profile.

Target-state recommendation:

- Add/standardize `profile` as a first-class field in UACP task metadata and council dispatch artifacts.
- Keep `runtime_surface` separate: `delegate_task`, `hermes_profile_process`, `hermes_kanban_worker`, `external_coding_agent`, `tool_or_evidence_adapter`, `human_operator`.
- Do not overload `profile` to mean Claude/Codex. Use `profile` for the Hermes controller identity and `runtime` for Claude/Codex/OpenCode/etc.

## Minimal profile configuration contract

Every UACP profile should declare at least:

```yaml
profile_id: uacp-...
positioning: one-sentence purpose
allowed_roles: []
default_council_modes: []
default_runtime_surface: delegate_task | hermes_kanban_worker | external_coding_agent | tool_or_evidence_adapter
model_policy:
  provider: ...
  model: ...
  fallback_chain: inherit_or_named_chain
  reasoning_effort: low | medium | high
permissions:
  toolsets: []
  write_scope: none | artifacts_only | declared_allowed_files | governed_workspace
  external_side_effects: forbidden | requires_approval | allowed_when_declared
context:
  workdir: UACP_ROOT | target_repo | task_defined
  skills: []
  memory: disabled | read_only | normal
routing:
  escalate_to_external_when: []
  prefer_native_when: []
evidence_obligations:
  required_outputs: []
  required_metadata:
    - profile_id
    - role
    - runtime_surface
    - model_provider
    - model
    - fallback_chain_id
    - toolsets
    - side_effects
    - verification_result
```


---

## Boundary correction: delegate_task is not a full council profile

The discovery that native `delegate_task` runs inside the parent profile changes the orchestration boundary.

UACP should classify `delegate_task` as an **ephemeral same-profile branch**, not as a full Agent Council member when profile diversity, separate doctrine, isolated memory, or stable role identity matters.

### Revised meaning of delegate_task

`delegate_task` is useful for:

- quick scratch analysis,
- bounded brainstorming branches,
- alternate wording drafts,
- focused file inspection,
- low-risk research synthesis,
- cheap same-profile second-pass critique,
- parallel decomposition where profile isolation is not needed.

`delegate_task` is not sufficient for:

- true profile-diverse Agent Council,
- profile-local `SOUL.md` / doctrine stack differences,
- different long-lived prompts or memory,
- durable review/debate rounds,
- worker identity that should be assigned, resumed, notified, or audited independently,
- external-runtime adapter behavior that must be governed as a stable role.

### New boundary terms

```text
same-profile branch = delegate_task
profile worker = Kanban-assigned Hermes profile or spawned hermes --profile process
runtime adapter = profile/tooling that invokes Claude Code, Codex, OpenCode, Kimi, etc.
```

### Agent Council implication

Agent Council should no longer assume native `delegate_task` equals a council expert.

There are now two council modes:

1. **Local scratch council** — same-profile, synchronous, uses `delegate_task`, good for fast brainstorming and provisional critique.
2. **Profile council** — profile-diverse, durable, uses Kanban/spawned profile workers, good for real Devil's Advocate, verifier, integrator critic, safety reviewer, or adapter roles.

A local scratch council can still be valuable, but its evidence confidence must be lower because all branches share the same profile doctrine, memory boundary, runtime process, and usually the same model/fallback policy.

### Can Kanban do debate/review?

Yes, but Kanban does not debate by itself.

Kanban can host debate/review as a durable task graph:

1. Orchestrator creates Round 1 tasks for reviewer profiles.
2. Each profile worker writes findings/proposals/comments/artifacts.
3. Orchestrator creates challenge tasks, e.g. Devil's Advocate reviews Round 1 outputs.
4. Integrator Critic or Orchestrator creates synthesis task.
5. Verifier checks the synthesis against evidence obligations.

This is slower than `delegate_task`, but it is the correct mechanism when the debate requires profile identity, persistence, notifications, independent prompt stacks, or auditability.

### Practical rule

Use `delegate_task` only when the question is:

> Can another same-profile branch help me think faster?

Use Kanban/profile workers when the question is:

> Do I need a different agent identity, prompt stack, model policy, permission boundary, or durable council participant?

Use external runtime adapters when the question is:

> Do I need a different execution runtime/toolchain or independent coding/review environment?


---

## Boundary correction: Kanban is an adapter, not the Agent Council substrate

Kanban must not become the hidden execution doctrine for UACP or Agent Council.

The earlier profile-worker design risks over-binding Agent Council to Hermes Kanban. That creates vendor/runtime lock-in: if profile-diverse debate only works through Hermes Kanban, then UACP becomes constrained by one coordination implementation instead of remaining runtime-neutral.

Canonical correction:

```text
Agent Council = adaptive deliberation protocol
Coordination substrate = replaceable adapter
Hermes Kanban = current coordination adapter, not the doctrine
```

Kanban may coordinate council work, but it must not define what council work is.

### Required separation

UACP should separate:

1. **Council protocol** — roles, rounds, debate state, challenge rules, regrouping, reruns, synthesis, findings, evidence obligations.
2. **Coordination adapter** — where tasks/comments/artifacts are stored and dispatched: Hermes Kanban today, another Kanban system later, Linear/GitHub Issues/Notion/custom queue in the future.
3. **Worker runtime** — Hermes profile, native delegate branch, Claude Code, Codex, OpenCode, Kimi, browser/evidence tool, human operator.
4. **State/evidence artifacts** — UACP-owned canonical records of what happened, independent of the coordination adapter.

### Debate cannot be passive-only

Kanban tasks alone are passive records. They cannot adaptively decide when to rerun, regroup, split roles, collapse roles, or escalate a debate.

Agent Council needs an active coordinator/orchestrator loop that can:

- inspect round outputs,
- detect missing or weak evidence,
- decide whether a role needs to rerun,
- add or remove roles,
- regroup tasks into a new debate round,
- escalate from scratch council to profile council or cross-runtime council,
- decide whether synthesis is mature enough for VERIFY,
- record why the debate ended.

Therefore a Kanban-hosted council must include an explicit coordinator task or orchestrator process. Do not rely on passive task completion alone.

### Adapter contract

Any coordination substrate used by Agent Council should implement a small contract:

```yaml
coordination_adapter:
  create_unit: required
  assign_unit: required
  declare_dependencies: required
  attach_context: required
  attach_artifact_or_comment: required
  read_unit_outputs: required
  mark_state: required
  watch_or_poll_state: optional
  notify: optional
  retry_or_rerun_unit: required
  preserve_provenance: required
```

Hermes Kanban is one implementation of this contract, not the contract itself.

### Revised council forms

```text
scratch_council:
  coordination: in-memory parent session
  workers: delegate_task same-profile branches
  durability: low

profile_council:
  coordination: coordination_adapter, currently Hermes Kanban
  workers: Hermes profiles / spawned profile processes
  durability: medium/high

cross_runtime_council:
  coordination: coordination_adapter + runtime adapters
  workers: Hermes profiles, external coding agents, evidence services, humans
  durability: high
```

### Design implication

Agent Council should own debate state and adaptive logic. Kanban should only persist/dispatch units.

If Hermes Kanban becomes too limiting, UACP should be able to swap in a custom council queue or another task substrate without rewriting the council protocol.


---

## Phase-specific coordination substrate rule

Not every UACP phase requires Kanban or another durable coordination adapter.

Canonical correction:

```text
Kanban/coordination adapter is mandatory only when durable multi-worker execution state is needed.
EXECUTE commonly requires it.
TRIAGE/PROPOSE/PLAN/VERIFY/RESOLVE may use it, but should not use it by default.
```

### Default phase guidance

- `TRIAGE`: normally no Kanban. Use direct reasoning or scratch branches. Create durable tasks only if intake itself becomes multi-party or long-running.
- `PROPOSE`: normally no Kanban. Use direct artifacts and optional scratch/profile council if authority, side effects, or scope need challenge.
- `PLAN`: no Kanban by default for ordinary plans. Use Kanban only when planning becomes a durable, multi-role planning project or when full automation requires tracked planning units.
- `EXECUTE`: usually the strongest Kanban/coordination-adapter candidate because execution needs durable ownership, dependencies, retries, allowed files, verification obligations, and progress tracking.
- `VERIFY`: no Kanban by default for simple verification. Use Kanban/profile council when verification is long-running, multi-role, cross-runtime, finding-driven, or requires reruns/regrouping.
- `RESOLVE`: normally no Kanban. Use artifacts and direct synthesis unless resolution tasks need durable follow-through.

### Full automation mode

For fully autonomous operation, every phase may be represented as command-bot / coordination-adapter tasks, but that is an automation topology, not a conceptual requirement.

In full automation mode:

```text
phase controller task
  -> selects profile/runtime/council form
  -> creates bounded phase work units if needed
  -> monitors outputs/timeouts/reruns
  -> writes phase artifact
  -> requests/executes phase transition
```

The phase controller may be implemented by a command bot, Hermes profile, or future UACP runtime controller. It should own the adaptive loop for that phase. Kanban/coordination adapter only stores and dispatches units.

### Insight / planning intelligence layer

Planning decisions should happen in the deliberative layer, not inside Kanban itself.

Call this layer `Insight` if useful: the phase-local reasoning/control loop that decides whether to use direct reasoning, `delegate_task`, a profile council, a runtime adapter, or durable coordination units.

```text
Insight / phase controller = decides topology
Coordination adapter = records/dispatches work units
Worker runtime = performs bounded work
UACP artifacts = canonical evidence/state
```

### Practical rule

Use no Kanban when the phase can complete synchronously with clear evidence.

Use Kanban/coordination adapter when the phase needs at least one of:

- durable multi-worker ownership,
- profile-specific workers,
- long timeout/background execution,
- dependencies between units,
- retry/rerun/regrouping,
- notification/resume across sessions,
- audit trail for worker outputs,
- external runtime coordination,
- full-autonomy command-bot execution.


---

## Current-stage profile policy: semi-auto/manual first

Current operating mode should be **semi-auto/manual execution first**, with a reserved design slot for future fully autonomous topology.

This changes how UACP role profiles should be interpreted today.

### Present capability boundary

At the current stage there are only two practical delegation paths:

1. `delegate_task`: synchronous same-profile branch. It cannot load a separate Hermes profile home.
2. Coordination-adapter task, currently Hermes Kanban: can target named profiles, but executes asynchronously/durably.

Therefore named UACP profiles such as `uacp-planner`, `uacp-verifier`, `uacp-devils-advocate`, and `uacp-integrator-critic` should **not** be treated as mandatory live workers for ordinary semi-auto/manual runs.

### What profiles mean in semi-auto/manual mode

In semi-auto/manual mode, profile names are primarily:

- future execution identities,
- role templates,
- prompt/config design targets,
- routing labels for when durable/asynchronous work is justified,
- documentation of what kind of worker should exist later.

They are not required to exist as active Hermes profiles for every PLAN/VERIFY/PROPOSE action.

### Practical rule

For current-stage UACP work:

- Use the main orchestrator for most TRIAGE/PROPOSE/PLAN/VERIFY/RESOLVE work.
- Use `delegate_task` for quick same-profile scratch analysis or provisional critique.
- Use Kanban/profile workers only for non-trivial EXECUTE work or when a phase explicitly needs durable profile-specific async coordination.
- Treat `uacp-planner` / `uacp-verifier` profile names as optional escalation targets, not default phase executors.

### Future-autonomy reservation

Keep the profile names and configuration contract because they reserve future topology slots:

```text
manual/semi-auto today:
  role templates and optional async profile workers

full-auto later:
  command-bot/phase-controller tasks dispatch named profiles per phase
```

This avoids premature complexity while preserving the architecture for full automation.
