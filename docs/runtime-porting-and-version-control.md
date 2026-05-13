# Runtime Porting And Version Control

Status: canonical policy seed  
Source: imported from `HERMES_ROOT/plans/uacp-runtime-proof-model-vc/10-runtime-porting-version-branch-control.md`  
First execution evidence: `executions/runtime-porting-20260513-symlink-proof.yaml`

## Purpose

UACP is the central Git-controlled source of truth for governed runtime adapter behavior. Runtime repositories such as Hermes Agent are downstream targets, not the long-term authority root for UACP-owned plugins, hooks, policy packs, or adapter source.

## Authority Model

```text
UACP doctrine/config/state
  -> runtime-neutral contracts
  -> runtime-adapters/<runtime>/...
  -> runtime-specific plugin/hook/config binding
  -> symlink/install/export into Hermes, OpenCode, Claude Code, Codex, Kimi, Gemini, or future runtimes
```

Runtime behavior must derive from UACP docs/config and must not become a hidden source of truth. Hermes is the first target runtime, not the conceptual boundary.

## Repository Policy

- `UACP_ROOT` owns governed doctrine, configs, plans, verification, audit artifacts, runtime contracts, and runtime adapters.
- `UACP_ROOT/main` represents stable reviewed UACP authority state.
- Active governed runtime-porting work uses local branches/worktrees named `uacp/<run-id>/<topic>`.
- A private remote is required for real backup; local Git alone is version history, not backup.
- Pushes to any remote are external side effects and require explicit operator confirmation.

## Hermes Runtime Adapter Policy

UACP-owned Hermes plugin source should live under `runtime-adapters/hermes/plugins/<plugin-name>/` and be consumed through `HERMES_ROOT/plugins/<plugin-name>` symlink bindings. Hermes Agent may temporarily contain duplicate plugin copies while proving the user-plugin binding, but UACP-specific plugin source should move out of the Hermes local patch after discovery and behavior tests pass.

## Binding Sequence

1. Ground-truth runtime discovery with a non-destructive symlink probe.
2. Copy/import candidate adapter source under `runtime-adapters/hermes/plugins/`.
3. Bind selected adapters into `HERMES_ROOT/plugins/` by symlink or equivalent runtime binding.
4. Verify manifest discovery, module loading, hook/tool registration, and affected runtime behavior.
5. Only then reduce duplicated Hermes Agent plugin source.
6. Record rollback commands and commit references for both UACP and runtime repos.

## Rollback Requirements

For a symlink binding, rollback must be executable without touching UACP source: remove the `HERMES_ROOT/plugins/<plugin-name>` symlink. If the Hermes Agent bundled copy was already removed, restore it from the local Hermes patch commit or upstream branch before restarting Hermes.

## Config Boundary

Sanitized Norty config templates may use a smaller config repository or Gist, but that is not UACP authority. Do not store secrets, `.env`, `auth.json`, `state.db`, sessions, logs, or private memory in Git/Gist.
