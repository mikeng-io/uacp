---
type: adr
title: Regroup runtime-adapters by runtime with a shared layer
description: Reorganize runtime-adapters/ by runtime (claude/ · kimi/ · codex/ · hermes/) plus a shared/ layer for cross-runtime logic, replacing the mixed by-mechanism (hooks/ + mcp/) organization, while keeping plugin manifests at their convention-mandated locations.
tags: [runtime-adapter, structure, hook, mcp, claude-code, kimi, codex, hermes]
timestamp: 2026-06-27
status: proposed
---

# Regroup runtime-adapters by Runtime with a Shared Layer

## Metadata

- **Status**: proposed
- **Date**: 2026-06-27
- **Decision Makers**: UACP maintainer
- **Consulted**: as-built `runtime-adapters/` (the `hooks/` + `mcp/` + `hermes/` tree); the Claude Code plugin manifest convention (`.claude-plugin/plugin.json` must live under `.claude-plugin/`; hooks.json is referenced by an explicit `plugin.json` `hooks` pointer and need not sit at the plugin root); the Kimi plugin manifest convention (`kimi.plugin.json`); ADR-0019 (PreToolUse shim narrow scope); ADR-0015 (web backends separate from bridge adapters)
- **Informed**: all agents; runtime-adapter / hook authors
- **Related**: ADR-0019 (the shim this regroup relocates), AGENTS.md Key Invariant #3, `runtime-adapters/README.md`

## Context and Problem Statement

`runtime-adapters/` mixed two organizing axes. `hermes/` was grouped **by
runtime**, while `hooks/` and `mcp/` were grouped **by mechanism**. The
by-mechanism grouping concealed real facts about the contents:

- `hooks/guardian_pretooluse.py` is a **cross-runtime** PreToolUse shim — it serves
  Claude Code *and* Kimi Code (via `--profile`), and is a candidate for any host
  that exposes a PreToolUse surface. It is not "a hook" so much as shared logic.
- `hooks/inject_uacp_md.py` is **Claude-Code-only** (a SessionStart cognition
  injector) yet sat in the same generic `hooks/` bucket as the cross-runtime shim,
  so the directory implied a uniformity that did not exist.
- `mcp/uacp_mcp_server.py` is **one server for all runtimes** — also shared logic,
  not a per-runtime artifact.

With more runtimes on the horizon (Codex, opencode), the by-mechanism layout had no
uniform home for "the wiring that makes runtime X work", and no place to say
"runtime X has no PreToolUse surface, so it is MCP-governed-only". A new runtime had
to scatter its files across `hooks/` and `mcp/` by mechanism, obscuring what is
shared versus what is runtime-specific.

## Decision Drivers

- **One axis.** Group by runtime, matching the already-present `hermes/`, so the
  directory answers "what makes runtime X work" in one place.
- **Name the shared layer explicitly.** Cross-runtime logic (the PreToolUse shim,
  the MCP server) should live in a layer named for being shared, not in a
  mechanism bucket that hides its reach.
- **Uniform extension.** Adding a runtime should be a thin per-runtime directory
  reusing the shared layer — including the honest degrade for a runtime with no
  hook surface.
- **Do not break plugin discovery.** Host plugin managers require manifests at
  convention-mandated locations; the regroup must change only their *internal*
  paths, never move the manifests themselves.
- **Keep the kernel neutral.** `hook_kernel.py` must not learn host names from this
  regroup.

## Considered Options

1. **Keep by-mechanism (`hooks/` + `mcp/`)** — *rejected.* Mixes axes with
   `hermes/`, hides that the shim and server are shared, and has no uniform home
   for a new runtime.
2. **Pure by-runtime, duplicate the shim per runtime** — *rejected.* Copies the
   cross-runtime shim into `claude/` and `kimi/`, inviting drift; the shim's whole
   point is that its predicate is identical across hosts.
3. **By-runtime + a `shared/` layer** — **chosen.** One axis, with cross-runtime
   logic factored into `shared/` (+ the existing `mcp/`), reused by thin
   per-runtime wiring directories.

## Decision Outcome

Reorganize the **implementation tree** by runtime, with a `shared/` layer; leave
the plugin **manifests** at their convention-mandated locations and update only
their internal command paths.

Target layout:

| Path | Role |
|---|---|
| `runtime-adapters/shared/guardian_pretooluse.py` | The cross-runtime PreToolUse Guardian shim (CC + Kimi via `--profile`). Moved from `hooks/`. |
| `runtime-adapters/mcp/uacp_mcp_server.py` | The one MCP governed-tools server, all runtimes. Unchanged. |
| `runtime-adapters/claude/inject_uacp_md.py` | Claude-Code-only SessionStart `UACP.md` injector. Moved from `hooks/`. |
| `runtime-adapters/claude/hooks.json` | The CC hook-registration manifest (SessionStart + PreToolUse). Moved from the plugin root; CC loads it via plugin.json's explicit `hooks` pointer, not by auto-discovery. |
| `runtime-adapters/claude/README.md` | Claude Code wiring (SessionStart injector + how CC registers the shared shim). |
| `runtime-adapters/kimi/README.md` | Kimi reuses `shared/` + `mcp/`; the shim is a manual `~/.kimi-code/config.toml` paste. |
| `runtime-adapters/codex/README.md` | Codex reuses `shared/` + `mcp/`; MCP-governed-only if it has no PreToolUse surface (honest degrade). |
| `runtime-adapters/hermes/…` | The existing Hermes plugins. Unchanged. |
| `runtime-adapters/shared/README.md` | The cross-runtime shim docs. |
| `runtime-adapters/README.md` | The map of the new layout (shared logic vs per-runtime wiring). |

**Shared logic vs per-runtime wiring.** The *behavior* — the `.uacp/` PreToolUse
predicate and the governed-tools server — is written once in `shared/` and `mcp/`.
The *wiring* — how a host discovers and invokes that behavior (a plugin manifest, a
`config.toml` paste, an MCP registration) — differs per host and lives in the
runtime's own directory.

**Convention-mandated manifests stay at their mandated roots; hooks.json moves
by-runtime.** Host plugin managers require `plugin.json` to live under
`.claude-plugin/`, and `kimi.plugin.json` at the plugin root — those do not move.
But CC's hook-registration manifest, `hooks.json`, is loaded via the **explicit**
`plugin.json` `hooks` pointer; CC has **no requirement** that it sit at the plugin
root (the auto-discovery default of `./hooks/hooks.json` is one option, not a
constraint). So `hooks.json` moves under `claude/` with the rest of CC's wiring,
and the explicit pointer makes it work — **install-verified**: `claude plugin
validate --strict` passes, a real `claude plugin install` registers both hooks, and
`claude plugin details uacp` reports `Hooks (2) SessionStart, PreToolUse`.
- `.claude-plugin/plugin.json` — stays at `.claude-plugin/` (convention-mandated).
  Its `hooks` pointer is **repointed** `"./hooks/hooks.json"` →
  `"./runtime-adapters/claude/hooks.json"`; its `mcpServers` arg
  `${CLAUDE_PLUGIN_ROOT}/runtime-adapters/mcp/uacp_mcp_server.py` stays (the MCP
  server did not move).
- `runtime-adapters/claude/hooks.json` — **moved** from the plugin root into the
  CC runtime directory. Its two command paths also move:
  `…/runtime-adapters/hooks/inject_uacp_md.py` →
  `…/runtime-adapters/claude/inject_uacp_md.py`;
  `…/runtime-adapters/hooks/guardian_pretooluse.py` →
  `…/runtime-adapters/shared/guardian_pretooluse.py`.
- `kimi.plugin.json` — stays at the plugin root (convention-mandated); references
  only the MCP server (unmoved); it carries no hooks path.

The movers stay two directories deep under the repo
(`runtime-adapters/<dir>/file.py`), so `guardian_pretooluse.py`'s
`_REPO_ROOT = Path(__file__).resolve().parents[2]` and `inject_uacp_md.py`'s
three-`dirname` plugin-root fallback remain correct.

### Positive Consequences

- One organizing axis; `runtime-adapters/` reads as "by runtime, plus a shared
  layer", and the directory map states shared-vs-wiring plainly.
- A new runtime is a thin per-runtime directory that reuses `shared/` + `mcp/`.
- A runtime with no hook surface has an explicit, honest home: MCP-governed-only
  (e.g. `codex/`).
- The cross-runtime shim has a single source of truth (`shared/`), so the CC and
  Kimi wirings cannot drift apart.
- `hook_kernel.py` stays runtime-neutral — no host names leak into the kernel.

### Negative Consequences

- A one-time churn of references: the relocation of `hooks.json` (plugin root →
  `runtime-adapters/claude/`), its internal command paths, the `plugin.json` `hooks`
  pointer, test path constants, and doc/config string references all had to move in
  lockstep. The regrep guard (`grep -rn "hooks/hooks.json"` and
  `grep -rn "runtime-adapters/hooks"` → zero outside this ADR's own migration notes)
  covers it.
- `shared/` is a slightly abstract bucket; if it ever grows beyond genuinely
  cross-runtime logic it could re-accrete the "mixed axis" smell. Kept disciplined
  by the rule: `shared/` holds only logic identical across runtimes.

## Validation

- `tests/unit/skills/test_hook_manifest.py` — `runtime-adapters/claude/hooks.json`
  PreToolUse command resolves to `runtime-adapters/shared/guardian_pretooluse.py`
  (exists), and `plugin.json`'s `hooks` pointer equals
  `./runtime-adapters/claude/hooks.json`.
- `tests/integration/test_pretooluse_hook.py` — the shim's full narrow-predicate
  matrix runs from its new `shared/` path (function-level + subprocess).
- `tests/integration/test_sessionstart_inject.py` — the injector runs from its new
  `claude/` path and still injects / fails open.
- `tests/unit/skills/test_mcp_manifests.py` — the MCP server path is unchanged and
  still resolves.
- `grep -rn "runtime-adapters/hooks"` and `grep -rn "hooks/hooks.json"` return zero
  operational references (only this ADR's own old→new migration arrows remain).
- `claude plugin validate <root> --strict` passes; a real `claude plugin install`
  registers both hooks (`claude plugin details uacp` → `Hooks (2) SessionStart,
  PreToolUse`).
- The full suite stays green.

## Related ADRs

- Relocates the shim narrowed in [ADR-0019](0019-pretooluse-hook-narrow-scope-and-invariant-3-clarification.md).
- Consistent with [ADR-0015](0015-web-backends-separate-from-bridge-adapters.md) (keep distinct adapter concerns in distinct homes).

## References

- Implementation: `runtime-adapters/shared/guardian_pretooluse.py`, `runtime-adapters/claude/inject_uacp_md.py`, `runtime-adapters/mcp/uacp_mcp_server.py`
- Map + per-runtime docs: `runtime-adapters/README.md`; `runtime-adapters/{shared,claude,kimi,codex}/README.md`
- Manifests: `.claude-plugin/plugin.json`, `runtime-adapters/claude/hooks.json`, `kimi.plugin.json`
