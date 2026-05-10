# UACP Lifecycle Reference

UACP governs work through a triage entry stage followed by a stable five-phase lifecycle:

```text
TRIAGE -> PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE
```

Triage decides whether the request should enter UACP at all, and at what governance intensity. Each later phase transition runs adaptive gate selection before deciding whether to proceed.

## TRIAGE

Purpose: calibrate scope, assign a granularity level, and route the request.

Typical routing outcomes:

- direct
- lightweight
- standard_uacp
- full_governance
- block_or_clarify

Typical artifacts:

- triage summary for Level 2+ work
- scoring factors: impact, reversibility, domain count, runtime count, verification difficulty
- granularity score
- routing outcome
- initial domains and artifact types
- authority, side-effect, and trust-boundary notes

Exit condition: request is routed to direct action, blocked for clarification, or admitted into `PROPOSE`.

Triage admission map:

| Outcome | Disposition |
|---|---|
| `direct` | No UACP lifecycle; handle directly with a lightweight record only when needed. |
| `lightweight` | Enter a minimal governed path with a small artifact footprint. |
| `standard_uacp` | Enter the normal UACP lifecycle at standard governance intensity. |
| `full_governance` | Enter the full lifecycle with councils, broader review, and durable learning. |
| `block_or_clarify` | Stop and request clarification or authority before proceeding. |

## PROPOSE

Purpose: define the requested work, authority, scope, affected domains, side effects, and risk.

Typical artifacts:

- proposal summary
- initial gate-selection artifact
- scope and non-goals
- authority and side-effect declaration

Exit condition: proposal is approved or explicitly blocked.

## PLAN

Purpose: transform the approved proposal into bounded execution, selected evidence clusters, review routing, and verification strategy.

Typical artifacts:

- execution plan
- Kanban task graph description
- selected PLAN clusters
- verification candidates
- write containment plan

Exit condition: execution can start with clear boundaries and acceptance evidence.

## EXECUTE

Purpose: perform bounded work through Hermes Kanban, delegated workers, external coding agents, or local tools as selected.

Typical artifacts:

- execution history
- changed artifact list
- worker reports
- side-effect log

Exit condition: planned execution units are complete or explicitly blocked.

## Hermes Kanban Binding

Hermes Kanban is a durable task substrate, not the UACP lifecycle state machine.

Confirmed Hermes Kanban semantics:

- storage is SQLite-backed and board-scoped,
- boards can isolate unrelated streams of work,
- task statuses are `triage`, `todo`, `ready`, `running`, `blocked`, `done`, and `archived`,
- parent links gate child tasks: children stay `todo` until all parents are `done`, then promote to `ready`,
- the dispatcher claims `ready` tasks with assignees and spawns worker profiles,
- workers complete, block, heartbeat, comment, or create follow-up tasks through Kanban tools,
- workspaces are declared as `scratch`, `dir`, or `worktree`,
- completion summaries and metadata are the structured handoff surface.

UACP must not assume Kanban knows UACP phases. UACP phase state must be recorded in UACP artifacts, while Kanban task IDs provide execution traceability.

Do not conflate:

- UACP `TRIAGE`: governance entry stage for scope calibration and routing.
- Hermes Kanban `triage`: task status for an underspecified Kanban card that needs specification before it becomes `todo`.

When UACP binds PLAN and EXECUTE to Hermes Kanban, it records:

- board slug,
- root task IDs,
- parent-child task graph,
- assignee/profile,
- workspace kind and path policy,
- completion summaries and metadata needed for VERIFY.

Active binding:

- `state/kanban.yaml` is the current binding artifact.
- `board_slug` is `uacp`.
- `root_task_ids` records the current binding anchor task ids for PLAN/EXECUTE traceability.
- `state/current.yaml` may point at the binding artifact for fast retrieval.

## State And Version-Control Design

UACP has an explicit state layer. The current implementation is file-based YAML with governed mutation routed through `uacp-state`.

Design decision:

- UACP has an initial `state/` layer.
- Active lifecycle state should be file-based YAML first, not SQLite first.
- SQLite or a standalone service can be added later for query, concurrency, or ranking needs.
- Git should version governance docs, config, schemas, tombstones, and durable audit artifacts.
- Runtime state changes should not require a git commit for every mutation.
- Historical audit artifacts should be append-only where practical.

State file shape should be small and pointer-based. A run manifest should record:

- run id,
- current UACP stage or phase,
- authority source,
- selected artifact paths,
- current transition artifact,
- council synthesis artifact when a checkpoint is reviewed,
- current phase transition artifact,
- selected evidence clusters,
- Kanban board slug and task IDs when Kanban is used,
- verification status,
- deferred items,
- latest update provenance.

During bootstrap, `current_stage` and `current_phase` had to match exactly. They remain aliases until `uacp-state` introduces a single canonical field or a strict derivation rule.
The bootstrap boundary is closed. `state/current.yaml` records `mutation_policy: uacp_state_required`, `bootstrap_closed: true`, and `governed_mutation_active: true`.

State mutation rule:

- Runtime state mutation goes through the dedicated `uacp-state` skill.
- Direct state edits are closed bootstrap behavior and require explicit recovery authorization if needed.
- Every state change must point to an authorizing artifact or phase transition.
- State must reference artifacts by `UACP_ROOT`-relative paths or symbolic roots, not physical deployment paths.

Version-control binding:

- `UACP_ROOT` is versioned as its own focused repository for UACP governance and durable audit artifacts.
- `HERMES_ROOT` may bind and host UACP, but should not be the implicit source of truth for UACP history unless explicitly chosen.
- Tombstone `git_commit` should point to the commit that deleted the legacy file and added or updated the tombstone. Agents can retrieve the deleted content from that commit's parent at the `deleted_path`.
- When no repository exists, tombstones use `unavailable-no-git-worktree` and must be updated after versioning is established.

Boundary definitions:

- Canonical governance: active docs and config listed in `docs/index.md`.
- Runtime state: current lifecycle position, current pointers, and run manifests under `state/`.
- Historical audit: proposals, plans, executions, verification artifacts, outputs, lessons, and tombstones.
- Knowledge artifacts: reusable scenarios, templates, lessons, and indexes under `knowledge/`, later eligible for Knowledge Bank ingestion.

Active implementation:

- `uacp-state` exists and owns governed runtime-state mutation.
- The lifecycle skill family exists under `HERMES_ROOT/skills/devops/uacp/`.
- Bootstrap direct edits are closed.
- Runtime Guardian/Heartgate enforcement remains a future hardening step; until then, skills and config provide policy-level governance.
- Do not treat Kanban as UACP phase state; only task ids and graphs belong there.

## VERIFY

Purpose: validate actual completed artifacts using context-selected evidence clusters.

VERIFY is adaptive. Software work may select tests, diff review, static analysis, runtime validation, security review, migration review, or rollback review. Research may select source grounding and contradiction checks. Marketing may select audience fit, claim grounding, brand fit, and compliance checks. Lifestyle planning may select safety, cost, availability, and preference fit.

Exit condition: verification evidence supports pass, accepted warn, or block.

## RESOLVE

Purpose: finalize outputs, archive artifacts, extract lessons, and decide whether memory or skill updates are warranted.

Typical artifacts:

- final output summary
- phase transition artifact to terminal
- learning artifact
- memory policy decision

Exit condition: run is resolved and lessons are stored in the appropriate substrate.

## Lifecycle Skill Contracts

The lifecycle phases are stable; the skill files that operate them are separate implementation artifacts. The skill contract is:

| Skill | Core responsibility | State/write boundary |
|---|---|---|
| `uacp-state` | Own governed state mutation, state transitions, and pointer updates. | Exclusive mutator for runtime state after bootstrap. |
| `uacp-triage` | Calibrate scope, score granularity, and route the request. | Writes triage artifacts only. |
| `uacp-propose` | Capture authority, scope, side effects, and proposal viability. | Writes proposal artifacts only. |
| `uacp-plan` | Convert approved proposals into bounded execution and verification strategy. | Writes plan artifacts and task graph references only. |
| `uacp-execute` | Dispatch bounded work through Kanban or delegated workers. | Writes execution history and run-side-effect records only. |
| `uacp-verify` | Validate completed work with adaptive evidence clusters. | Writes verification artifacts only. |
| `uacp-resolve` | Finalize outputs, lessons, and memory or skill update decisions. | Writes resolution and learning artifacts only. |

Implementation status:

- Lifecycle skill files have been created after checkpoint review.
- Each skill file must read `docs/index.md` first and follow the canonical lifecycle and path rules.
- Skill files are implementation artifacts, not new governance sources of truth.

## Artifact Schemas

Seed schemas for the main UACP artifacts are defined in:

- `config/gate-selection.yaml`
- `config/evidence-clusters.yaml`
- `config/phase-transitions.yaml`
- `config/review-routing.yaml`
- `config/memory-policy.yaml`
- `config/state.yaml`

The schemas cover:

- gate-selection artifact
- triage artifact
- evidence cluster artifact
- learning artifact
- phase transition artifact
- run state artifact
- current state pointer
