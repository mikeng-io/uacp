---
type: spec
title: UACP Worktree Isolation Protocol
description: Protocol preventing active UACP runs from writing directly to main/master, defining workspace kinds and their lifetimes.
tags: [worktree, isolation, branching, write-containment]
timestamp: 2026-06-18
---

# UACP Worktree Isolation Protocol

Version: 1.0  
Derives from: Constitution Article IV.19, `runtime-porting-version-control.md`

---

## Purpose

Prevent active UACP runs from writing directly to `main`/`master`. Every run that enters TRIAGE must have a designated isolated workspace. This document defines when, how, and by whom the workspace is created, used, and destroyed.

---

## Rule

> **main is stable reviewed authority state. No active run may write to it.**

Violations are recorded as `guardian.block` or `heartgate.blocker` depending on when detected.

---

## Placement (mandatory)

> **A worktree MUST live under `$UACP_ROOT/.worktrees/<run-id>` — inside the repo. Never a sibling directory (`../uacp-<topic>`) and never an absolute path outside `$UACP_ROOT`.**

**Why this is a hard rule, not a preference.** Code-intelligence tooling roots at `$UACP_ROOT` and only indexes paths *under* it: the editor/agent **LSP language server**, a **SCIP / code indexer**, test runners, and the future UACP **code plane**. A worktree created as a *sibling* is **invisible** to all of them — workspace-wide symbol search / find-references silently return results from the *main* checkout (often a stale branch), not your working tree, which is dangerous (you reason about the wrong code). Nesting the worktree under `$UACP_ROOT/.worktrees/` keeps it inside the single tooling root so symbol search, references, and indexing see the live work. `.worktrees/` is gitignored (see PROPOSE below), so the nested checkout is never committed.

`.worktrees/` is **top-level by design — NOT under `.uacp/`**, which is the governed *runtime* namespace owned by the governed writers and the Guardian `state.uacp`/`artifact.uacp` path rules; developer checkouts must not be mixed into it.

---

## Workspace Kinds

| Kind | When to use | Lifetime |
|---|---|---|
| `worktree` | Default for software/code work. Git worktree on `uacp/<run-id>/<topic>` branch. | Created at PROPOSE, destroyed after RESOLVE merge. |
| `branch` | Lightweight work that shares the working directory but isolates commits. | Created at PROPOSE, merged after RESOLVE. |
| `dir` | Non-code work (docs, research, creative) where git branching is unnecessary. | Created at PLAN, archived after RESOLVE. |
| `scratch` | Ephemeral exploration, experiments, or temporary files. | Created on demand, deleted after use. |

---

## Phase-by-Phase Worktree Actions

### TRIAGE — Decide Isolation Need

- If the scope involves code changes, file mutations, or state updates: **require isolation**.
- Record `workspace_required: true` in the triage artifact.
- If `workspace_required: false` (pure research, no writes), `workspace_kind: scratch` is acceptable.

### PROPOSE — Declare Workspace

The proposal artifact must contain:

```yaml
workspace:
  kind: worktree | branch | dir | scratch
  path: ".worktrees/<run-id>"   # MANDATORY: under $UACP_ROOT/.worktrees/ — never a sibling or an absolute path outside $UACP_ROOT (see Placement rule)
  branch: "uacp/<run-id>/<topic>"  # if kind == worktree or branch
  created_by: propose
  rationale: "Why this kind was selected"
```

If `kind: worktree` or `branch`, create it now:

```bash
cd "$UACP_ROOT"
git worktree add ".worktrees/<run-id>" -b "uacp/<run-id>/<topic>"
```

**Requirement:** `.worktrees/` must be gitignored. Verify before creation:

```bash
git check-ignore -q .worktrees || { echo "ERROR: .worktrees not ignored"; exit 1; }
```

### PLAN — Validate Workspace

- Confirm workspace exists and is accessible.
- Confirm all `write_paths` in the plan resolve within the workspace.
- Record `workspace_validated: true` in the plan scope.
- If workspace is missing or `write_paths` escape it, block PLAN→EXECUTE.

### EXECUTE — Work in Workspace

- All file writes go to the declared workspace.
- Commit meaningful slices as work progresses:
  - After proposal approved
  - After plan finalized
  - After significant implementation milestones
  - After verification evidence collected
- Do not commit to `main`.

### VERIFY — Verify from Workspace

- Run verification against the workspace state.
- No new file writes except verification artifacts.
- Verification artifacts should be committed to the workspace branch.

### RESOLVE — Merge or Archive

- Final review of workspace contents.
- If merging to `main`:
  ```bash
  cd "$UACP_ROOT"
  git merge --ff-only "uacp/<run-id>/<topic>"
  ```
  Merge requires **operator approval**.
- If archiving without merge (e.g., experiment, rejected proposal):
  ```bash
  git tag "archive/uacp/<run-id>" "uacp/<run-id>/<topic>"
  git branch -D "uacp/<run-id>/<topic>"
  git worktree remove ".worktrees/<run-id>"
  ```
- Record workspace disposition in the resolve artifact.

---

## Worktree Maintenance Across the Lifecycle

| Concern | Rule |
|---|---|
| **Creation** | PROPOSE phase. Before any writes. |
| **Persistence** | Lives until RESOLVE. Survives phase transitions. |
| **State tracking** | `run_manifest.workspace` records kind, path, branch. |
| **Commit policy** | Commit at phase boundaries and significant milestones. Not every mutation. |
| **Cross-run isolation** | Two runs with overlapping `write_paths` must use separate worktrees. Heartgate blocks PLAN→EXECUTE if overlap detected. |
| **Main protection** | Guardian blocks direct writes to `main` when `governed_mutation_active: true`. |

---

## State Machine Integration

The `RunManifest` carries workspace metadata:

```yaml
# In state/runs/<run_id>.yaml
run_id: "uacp-20260607-brainstorm-audit"
status: active
current_phase: execute
workspace:
  kind: worktree
  path: ".worktrees/uacp-20260607-brainstorm-audit"
  branch: "uacp/uacp-20260607-brainstorm-audit/brainstorm-fixes"
  created_at: "2026-06-07T19:15:00Z"
  validated_at: "2026-06-07T19:20:00Z"
```

---

## Failure Modes

| Failure | Detection | Response |
|---|---|---|
| Workspace not created by PROPOSE | Guardian check at PLAN entry | Block, require workspace declaration |
| `write_paths` escape workspace | Heartgate at PLAN→EXECUTE | Block, fix plan or expand workspace |
| Direct write to `main` during EXECUTE | Guardian file-system hook | Block, redirect to workspace |
| Worktree directory not ignored | PROPOSE creation check | Warn, add to `.gitignore` before proceeding |
| Merge conflict at RESOLVE | `git merge` failure | Operator resolution required |

---

## Example

```bash
# TRIAGE decides: this needs isolation
# PROPOSE creates:
cd /Users/mike/Workplace/uacp
git worktree add .worktrees/uacp-20260607-brainstorm-audit \
  -b uacp/uacp-20260607-brainstorm-audit/brainstorm-fixes

# PLAN validates: write_paths = ["skills/uacp-brainstorm/", "docs/policy/"]
# All paths resolve within UACP_ROOT → workspace boundary is UACP_ROOT itself
# EXECUTE works in the worktree:
cd .worktrees/uacp-20260607-brainstorm-audit
# ... make changes ...
git add -A && git commit -m "brainstorm: add manifest.yaml and anti-collapse rules"

# VERIFY runs tests
# RESOLVE merges (after operator approval):
cd /Users/mike/Workplace/uacp
git merge --ff-only uacp/uacp-20260607-brainstorm-audit/brainstorm-fixes
git worktree remove .worktrees/uacp-20260607-brainstorm-audit
```
