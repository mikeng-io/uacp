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
4. Runtime state records the current run pointers and operational checkpoint evidence.
5. Skills and runtime behavior implement the documented rules.
6. Execution artifacts record what happened in a specific run.

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
4. `docs/orchestration-model.md` when multi-agent orchestration, council review, runtime adapters, or downstream agent-skill extraction are involved
5. Relevant config under `config/`
6. Supporting docs only when the current task needs them

For design or governance changes, also read:

- `docs/first-principles.md`
- `docs/alignment-spec.md`
- `docs/decision-log.md`

## Document Classes

| Class | Purpose | Creation rule |
|---|---|---|
| constitution | Non-waivable principles and invariants | One canonical file only |
| reference | Stable workflow, lifecycle, and user-facing model | Few canonical files; update existing before adding |
| policy | Operational rules for governance behavior | Prefer sections in canonical docs unless policy is large |
| schema_config | Machine-readable rules and artifact shapes | Lives under `config/`; must parse as YAML |
| runtime_state | Mutable run state and current pointers | Governed through `uacp-state` after bootstrap closure |
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
| `docs/alignment-spec.md` | reference | canonical | Artifact root layout and generic alignment conventions | Update when generic artifact conventions change; deployment-specific preferences live in the Hermes/Norty deployment notes section |
| `docs/runtime-enforcement.md` | reference / policy | canonical | Guardian and Heartgate runtime enforcement design | Update before runtime enforcement implementation changes |
| `docs/runtime-porting-and-version-control.md` | reference / policy | canonical | Runtime adapter ownership, runtime binding, repository/branch/worktree policy, and Hermes local-patch reduction path | Update before changing runtime adapter ownership or binding policy |
| `docs/orchestration-model.md` | reference | canonical | Agent Council, council modes/tiers, runtime adapters, and downstream orchestration vocabulary | Update before changing multi-agent orchestration semantics or downstream agent-skill extraction |
| `docs/runtime-integration-guide.md` | reference | canonical | Integration contract for new runtime adapters (Guardian event schema, Heartgate contract, binding sequence, verification checklist) | Update before changing adapter integration requirements |
| `docs/decision-log.md` | decision_log | canonical | Durable record of major UACP decisions | Append entries when major decisions are made; do not edit past entries |
| `config/evidence-clusters.yaml` | schema_config | generated | Evidence cluster families and schema | Keep aligned with canonical docs; YAML must parse |
| `config/gate-selection.yaml` | schema_config | generated | Meta-gate, triage scoring, gate-selection schema | Keep aligned with lifecycle and constitution |
| `config/phase-transitions.yaml` | schema_config | generated | Stage/phase transitions and transition artifact schema | Keep aligned with lifecycle reference |
| `verification/*heartgate*coherence*.yaml` | evidence_artifact | generated | Heartgate Council / transition-boundary coherence evidence | Reference from phase transition `heartgate_coherence.artifact_path` when used |
| `config/review-routing.yaml` | schema_config | generated | Review intensity and routing rules | Keep aligned with triage scoring and risk model |
| `config/memory-policy.yaml` | schema_config | generated | Memory, artifact, and future Knowledge Bank boundaries | Keep aligned with alignment spec |
| `config/roots.yaml` | schema_config | generated | Symbolic roots and path-resolution rules | Keep aligned with path convention in this registry |
| `config/state.yaml` | schema_config | generated | File-based state layer and version-control binding | Keep aligned with lifecycle reference and active `uacp-state` policy |
| `config/guardian-policy.yaml` | schema_config | generated | Machine-readable Guardian and Heartgate policy seed | Keep aligned with runtime enforcement design |
| `config/runtime-bindings.yaml` | schema_config | generated | Runtime adapter source and downstream runtime binding map | Keep aligned with runtime-porting policy and verified runtime discovery |
| `config/version-control.yaml` | schema_config | generated | UACP repository, branch/worktree, remote-backup, and commit-boundary policy | Keep aligned with runtime-porting policy and state/version-control docs |
| `state/` | runtime_state | canonical | Mutable run state layer | Keep pointer-based; mutate through `uacp-state` after bootstrap closure |
| `state/current.yaml` | runtime_state | canonical | Active state pointer | Update with the current run manifest and provenance |
| `state/kanban.yaml` | runtime_state | canonical | Active Hermes Kanban binding | Update when the board slug or root task ids change |
| `state/runs/` | runtime_state | canonical | Per-run manifests and checkpoint records | Append new run manifests; do not overwrite historical runs |
| `runtime-adapters/` | runtime_adapter_source | canonical | UACP-owned runtime adapter/plugin source for Hermes and future runtimes | Source changes require runtime binding verification and rollback evidence |

## Lifecycle Skill Registry

The lifecycle skill family is implemented under `HERMES_ROOT/skills/devops/uacp/`.
Skills implement the governed workflow; they do not override this registry, canonical docs, or config.

| Skill | Symbolic path | Status |
|---|---|---|
| `uacp-state` | `HERMES_ROOT/skills/devops/uacp/uacp-state/SKILL.md` | active |
| `uacp-triage` | `HERMES_ROOT/skills/devops/uacp/uacp-triage/SKILL.md` | active |
| `uacp-propose` | `HERMES_ROOT/skills/devops/uacp/uacp-propose/SKILL.md` | active |
| `uacp-plan` | `HERMES_ROOT/skills/devops/uacp/uacp-plan/SKILL.md` | active |
| `uacp-execute` | `HERMES_ROOT/skills/devops/uacp/uacp-execute/SKILL.md` | active |
| `uacp-verify` | `HERMES_ROOT/skills/devops/uacp/uacp-verify/SKILL.md` | active |
| `uacp-resolve` | `HERMES_ROOT/skills/devops/uacp/uacp-resolve/SKILL.md` | active |

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
5. Authority-changing decision log entries must reference the accepted checkpoint artifact and the exact canonical targets they modify.
6. Mark temporary notes as folded, promoted, deleted, or tombstoned.
7. Verify changed YAML files parse.

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

The durable decision log has been extracted to `docs/decision-log.md`. Major governance decisions are recorded there with rationale, status, and canonical targets.

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
- Define commit cadence for active runtime state now that `uacp-state` exists.
- Keep `outputs/uacp-current-status.yaml` current at major checkpoints; update to reflect the 2026-05-15 documentation hardening milestone.
- Process any future doc-sync drift through a new governed Kanban task; `t_9f0f686b` is already closed.
- After live proof tests, update `docs/runtime-enforcement.md` and the current status artifact with the tested activation state.
- Configure a private remote for `UACP_ROOT`; local Git history is not backup.
- Keep `docs/runtime-integration-guide.md` aligned when the Guardian event schema, Heartgate validation contract, or required tool registrations change.
