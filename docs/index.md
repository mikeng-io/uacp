# UACP Document Registry

This is the front door for UACP documentation. If an agent needs to understand or update UACP, start here.

## Purpose

UACP documents must be governed. New decisions should not automatically create new files. Every document needs a role, status, authority level, update rule, and retirement path.

The governed document set is the source of truth for UACP. Runtime frameworks, skills, configs, agents, councils, and execution tools must derive behavior from this documented authority. If the documents are unmanaged, the runtime layer will drift and UACP will become chaotic.

This registry controls:

- what documents exist,
- which documents are canonical,
- what order to read them in,
- where new decisions should be recorded,
- when a new document is allowed,
- when a document should be folded, deleted, tombstoned, or exceptionally archived.

## Source Of Truth Rule

UACP authority flows in this order:

1. `docs/index.md` defines the active document map and decision log.
2. Canonical prose docs define intent, principles, lifecycle, and policy.
3. YAML config encodes machine-readable rules derived from canonical docs.
4. Skills and runtime behavior implement the documented rules.
5. Execution artifacts record what happened in a specific run.

When these conflict, earlier layers win unless a newer decision log entry explicitly changes the authority chain.

Runtime behavior must not become the hidden source of truth. If an agent, skill, config, or implementation starts relying on undocumented behavior, the documentation must be updated or the behavior must be rejected.

## Context Hygiene Rule

Only active documents listed in the current inventory should be loaded by default. Deleted, tombstoned, archived, or historical documents must not be loaded unless the task explicitly requires legacy conflict analysis.

LLM context is a scarce execution surface. Keeping obsolete documents in the active tree risks stale context, false authority, and hallucinated reconciliation. Prefer deletion plus a short machine-readable tombstone entry.

## Read Order

For most work, read in this order:

1. `docs/index.md`
2. `docs/constitution.md`
3. `docs/lifecycle-reference.md`
4. Relevant config under `config/`
5. Supporting docs only when the current task needs them

For design or governance changes, also read:

- `docs/first-principles.md`
- `docs/alignment-spec.md`
- current decision log in this file

## Document Classes

| Class | Purpose | Creation rule |
|---|---|---|
| constitution | Non-waivable principles and invariants | One canonical file only |
| reference | Stable workflow, lifecycle, and user-facing model | Few canonical files; update existing before adding |
| policy | Operational rules for governance behavior | Prefer sections in canonical docs unless policy is large |
| schema_config | Machine-readable rules and artifact shapes | Lives under `config/`; must parse as YAML |
| runtime_state | Mutable run state and current pointers | Bootstrap only until `uacp-state` exists |
| decision_log | Durable record of major decisions | Prefer entries in this file, not standalone docs |
| working_note | Temporary exploration or transition note | Must be folded, promoted, deleted, or tombstoned |
| tombstone | Short pointer to deleted legacy material | Stored in this registry; no full stale document |
| archive | Retired historical material | Rare exception; requires explicit justification |

## Naming Convention

Use names that are stable for agents:

- active prose docs: lowercase kebab-case, `.md`
- config files: lowercase kebab-case, `.yaml`
- artifact files: `<run-id>-<artifact-kind>.yaml`
- tombstone `legacy_id`: `deleted-doc.<deleted-basename-without-extension>`

Avoid date-based filenames for canonical docs. Git history is the retrieval coordinate for legacy content. Human-readable dates may appear in decision headings, but machines should rely on names, paths, and commit pointers.

## Path Convention

Use symbolic roots and relative paths in UACP authority documents:

- `UACP_ROOT`: the directory containing `docs/`, `config/`, `proposals/`, and the other UACP artifact directories.
- `HERMES_ROOT`: the parent Hermes workspace that contains `UACP_ROOT`.
- `PRIVATE_ROOT`: sensitive external private data boundary.

Canonical docs, config, and runtime-state artifacts must use paths relative to `UACP_ROOT`, such as `docs/index.md`, `config/gate-selection.yaml`, or `state/current.yaml`. Do not hardcode a local deployment path into UACP authority documents.

Relative paths are not resolved against the agent's current shell directory. They are resolved against `UACP_ROOT` unless a different symbolic root is explicitly declared.

Path rules:

- Prefer `UACP_ROOT`-relative paths for UACP docs, configs, artifacts, state files, and knowledge files.
- Use symbolic roots for external boundaries, such as `HERMES_ROOT/skills/` or `PRIVATE_ROOT`.
- Do not use environment-specific absolute paths in canonical docs or generated config.
- Do not use `..` path traversal in UACP authority documents.
- Do not rely on the current working directory.
- If a physical deployment path is needed, bind `UACP_ROOT` outside the canonical docs and record why the physical path is unavoidable.

Relative-path risk: plain relative paths can be ambiguous if an agent resolves them from the wrong working directory. UACP avoids that by making `UACP_ROOT` the required base for all unqualified UACP-local paths. If a file cannot be expressed this way, the file must state why.

## Authority Levels

| Level | Meaning |
|---|---|
| canonical | Source of truth for current UACP behavior |
| supporting | Explains or expands canonical behavior |
| draft | Not yet authoritative |
| working | Temporary; must be resolved |
| tombstoned | Deleted from active docs; represented only by a short registry pointer |
| generated | Machine-readable config or schema seed |

## Current Inventory

| Path | Class | Authority | Role | Update rule |
|---|---|---|---|---|
| `docs/index.md` | decision_log / policy | canonical | Document registry and control framework | Update before adding or removing UACP docs |
| `docs/constitution.md` | constitution | canonical | Non-waivable invariants and governance constraints | Change rarely; requires explicit decision log entry |
| `docs/first-principles.md` | reference | canonical | Reasoning principles behind UACP | Update when core philosophy changes |
| `docs/lifecycle-reference.md` | reference | canonical | Current workflow and phase/stage model | Primary place for lifecycle wording |
| `docs/alignment-spec.md` | reference | canonical | Hermes/Norty integration alignment | Update when integration boundaries change |
| `config/evidence-clusters.yaml` | schema_config | generated | Evidence cluster families and schema | Keep aligned with canonical docs; YAML must parse |
| `config/gate-selection.yaml` | schema_config | generated | Meta-gate, triage scoring, gate-selection schema | Keep aligned with lifecycle and constitution |
| `config/phase-transitions.yaml` | schema_config | generated | Stage/phase transitions and transition artifact schema | Keep aligned with lifecycle reference |
| `config/review-routing.yaml` | schema_config | generated | Review intensity and routing rules | Keep aligned with triage scoring and risk model |
| `config/memory-policy.yaml` | schema_config | generated | Memory, artifact, and future Knowledge Bank boundaries | Keep aligned with alignment spec |
| `config/roots.yaml` | schema_config | generated | Symbolic roots and path-resolution rules | Keep aligned with path convention in this registry |
| `config/state.yaml` | schema_config | generated | File-based state layer and version-control binding | Keep aligned with lifecycle reference and future `uacp-state` |
| `state/` | runtime_state | canonical | Mutable run state layer | Keep pointer-based; bootstrap-only until governed mutation exists |
| `state/current.yaml` | runtime_state | canonical | Active state pointer | Update with the current run manifest and provenance |
| `state/runs/` | runtime_state | canonical | Per-run manifests and checkpoint records | Append new run manifests; do not overwrite historical runs |

## Creation Rules

Before creating a new UACP document, answer:

1. Can this decision be recorded in the decision log below?
2. Can the content update an existing canonical document?
3. Is this content temporary enough to be a working note?
4. Does the new file have a distinct reader, purpose, and maintenance owner?
5. What is the retirement path?

Create a new standalone document only when the answer to 1 and 2 is no, and the document has a durable role.

## Update Rules

When making a UACP documentation change:

1. Start at this registry.
2. Identify the target canonical document.
3. Update config only after the prose source of truth is clear.
4. Add a decision log entry for major lifecycle, governance, memory, routing, or document-structure changes.
5. Mark temporary notes as folded, promoted, deleted, or tombstoned.
6. Verify changed YAML files parse.

## Retirement Rules

A document should not remain as an unmanaged extra file.

Use these outcomes:

- `folded`: content moved into a canonical document.
- `promoted`: working note became canonical or supporting.
- `deleted`: default for temporary, retired, or obsolete documents.
- `tombstoned`: a short registry entry records why the document was deleted and where to retrieve it from version history.
- `archived`: rare exception when a non-active file must remain physically present.

Do not keep full suppressed documents in the active UACP tree. If legacy content is needed, retrieve it from version control using the tombstone entry.

## Tombstone Convention

Tombstones are for machines first. Keep them short.

Required fields:

- `legacy_id`
- `deleted_path`
- `intent`
- `rationale`
- `replacement_authority`
- `git_commit`

No timestamp is required. The git commit is the retrieval coordinate. If no git commit exists, use `unavailable-no-git-worktree` and update it after the artifact root is versioned.

## Decision Log

### 2026-05-10 — Add TRIAGE Before PROPOSE

Decision: UACP starts with `TRIAGE`, then enters `PROPOSE -> PLAN -> EXECUTE -> VERIFY -> RESOLVE` when governance is warranted.

Rationale: `PROPOSE` was too heavy as the first step. Simple work needs a way to exit without a full UACP run, while strategic work needs early governance-intensity scoring.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/gate-selection.yaml`
- `config/phase-transitions.yaml`
- `config/review-routing.yaml`

Follow-up: complete. The temporary working note was deleted after canonical docs and configs captured the decision.

### 2026-05-10 — Derive Granularity From Multiple Factors

Decision: TRIAGE does not use depth alone. It scores impact, reversibility, domain count, runtime count, and verification difficulty, then derives granularity and routing.

Rationale: A shallow task can be high impact or irreversible. A deep task can be low risk when reversible and easy to verify.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/gate-selection.yaml`
- `config/review-routing.yaml`

### 2026-05-10 — Establish Document Control Before More Design Expansion

Decision: `docs/index.md` becomes the document registry, read-order guide, and decision log for UACP documentation.

Rationale: UACP should not accumulate unmanaged docs, configs, working notes, and decision files. Document governance must exist before continuing broader workflow design.

Status: accepted.

Canonical target:

- `docs/index.md`

### 2026-05-10 — Delete Temporary TRIAGE Working Note

Decision: Delete `docs/triage-and-workflow-execution.md` instead of keeping it as an archived document.

Rationale: The file was a short-lived working note. Its durable decisions are now represented in `docs/index.md`, `docs/lifecycle-reference.md`, `config/gate-selection.yaml`, `config/phase-transitions.yaml`, and `config/review-routing.yaml`.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `docs/lifecycle-reference.md`
- `config/gate-selection.yaml`
- `config/phase-transitions.yaml`
- `config/review-routing.yaml`

### 2026-05-10 — Clarify Hermes Kanban Binding

Decision: UACP treats Hermes Kanban as a durable task substrate, not as the UACP lifecycle state machine.

Rationale: Hermes Kanban has its own statuses, boards, dispatcher, parent gating, workers, and workspace model. UACP must record phase state in UACP artifacts and use Kanban task IDs for execution traceability. UACP `TRIAGE` must not be confused with Hermes Kanban `triage` task status.

Status: accepted.

Canonical targets:

- `docs/lifecycle-reference.md`
- future PLAN/EXECUTE binding artifacts

### 2026-05-10 — Close Stage 1/2 Foundation

Decision: Stage 1/2 foundation is closed with deferred implementation items.

Rationale: UACP now has its artifact directories, canonical docs, seed config, document registry, symbolic root policy, TRIAGE model, bootstrap triage artifact, verification artifact, and clarified Hermes Kanban boundary. Further work should move to state/version design and later implementation rather than continuing to expand Stage 1/2.

Status: accepted.

Deferred items:

- version-control binding,
- state model implementation,
- lifecycle skill skeletons,
- Hermes Kanban binding,
- standalone Knowledge Bank service.

Canonical targets:

- `docs/index.md`
- `docs/lifecycle-reference.md`
- `verification/uacp-bootstrap-stage-1-2-verification.yaml`

### 2026-05-10 — Design State And Version-Control Layer

Decision: UACP should use a `state/` layer with file-based YAML run manifests first, governed mutation through future `uacp-state`, and git versioning for governance/history artifacts. SQLite or service-backed state is deferred until query or concurrency needs justify it.

Rationale: UACP phase state must be explicit and separate from Hermes Kanban task status. File-based YAML is inspectable, portable, and sufficient for bootstrap. Git should preserve governance and tombstone history, but runtime state should not require committing every mutation.

Status: design accepted; implementation deferred.

Canonical targets:

- `docs/lifecycle-reference.md`
- `config/state.yaml`

### 2026-05-10 — Seed File-Based State Layer

Decision: Create the initial file-based state contract and bootstrap run state under `state/`.

Rationale: UACP needs explicit lifecycle state before lifecycle skills or Kanban integration can be safe. The first implementation should remain inspectable and portable: a `state/current.yaml` pointer plus run manifests under `state/runs/`, governed by `config/state.yaml`.

Status: accepted.

Canonical targets:

- `config/state.yaml`
- `state/current.yaml`
- `state/runs/uacp-bootstrap-stage-3-state-binding.yaml`

### 2026-05-10 — Require Agent Council At State/Version Checkpoint

Decision: The state/version-control checkpoint requires a full-dimension local Agent Council review before the milestone can close or lifecycle skills can be created.

Rationale: State and version-control decisions define UACP's mutation boundary. A single orchestrator pass is not enough; the checkpoint needs role-diverse review across document authority, state traceability, versioning, Kanban boundary, adaptive gates, memory/knowledge boundaries, path containment, non-software coverage, and operational feasibility.

Status: accepted.

Canonical targets:

- `config/review-routing.yaml`
- current checkpoint council artifact under `verification/`

### 2026-05-10 — Register Runtime State In The Active Inventory

Decision: `state/`, `state/current.yaml`, and `state/runs/` are part of the governed UACP artifact root and must be enumerated in the active inventory.

Rationale: The lifecycle reference now treats runtime state as first-class, so the registry must expose it rather than leaving it implicit.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `docs/alignment-spec.md`
- `config/state.yaml`
- `state/current.yaml`
- `state/runs/uacp-bootstrap-stage-3-state-binding.yaml`

Follow-up: `state/` remains bootstrap-only until `uacp-state` exists.

### 2026-05-10 — Tighten Tombstone And Path Rules

Decision: Canonical docs, config, and runtime-state artifacts must use `UACP_ROOT`-relative paths by default, and tombstones using `unavailable-no-git-worktree` must be revisited after version-control binding exists.

Rationale: Context hygiene is better when the active tree is portable, and placeholder tombstone provenance should not become permanent after the artifact root is versioned.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `config/roots.yaml`

### 2026-05-10 — Establish UACP_ROOT Git Binding

Decision: `UACP_ROOT` is a standalone git repository for UACP governance, state, and durable audit artifacts.

Rationale: UACP needs an explicit commit boundary for tombstones, durable audit records, and version-linked governance. A standalone repository keeps that boundary visible and avoids coupling UACP history to unrelated runtime repos.

Status: accepted.

Canonical targets:

- `docs/index.md`
- `config/state.yaml`
- `state/current.yaml`
- `state/runs/`

Follow-up: active runtime-state commit cadence remains deferred until `uacp-state` exists.

## Tombstones

```yaml
- legacy_id: deleted-doc.triage-and-workflow-execution
  deleted_path: docs/triage-and-workflow-execution.md
  intent: remove short-lived working note from active UACP context
  rationale: canonical docs and config now carry the TRIAGE decision; retaining the full working note would risk stale context loading
  replacement_authority:
    - docs/index.md
    - docs/lifecycle-reference.md
    - config/gate-selection.yaml
    - config/phase-transitions.yaml
    - config/review-routing.yaml
  git_commit: e7fcb8e
```

## Open Document Actions

- Keep tombstone commit pointers aligned with the repository history that owns `UACP_ROOT`.
- Replace bootstrap direct state edits with `uacp-state` once lifecycle skills are created.
- Define commit cadence for active runtime state once `uacp-state` exists.
