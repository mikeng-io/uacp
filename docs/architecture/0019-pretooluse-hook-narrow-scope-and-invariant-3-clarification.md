---
type: adr
title: PreToolUse hook narrow scope and Invariant #3 clarification
description: Narrow the Claude Code / Kimi Code Guardian PreToolUse shim to a single accidental-corruption guard over the .uacp/ namespace, and clarify AGENTS.md Key Invariant #3 to distinguish governed-state writes from work-product writes.
tags: [hook, guardian, runtime-adapter, invariant, governed-writers, defense-in-depth]
timestamp: 2026-06-26
status: proposed
---

# PreToolUse Hook Narrow Scope and Invariant #3 Clarification

## Metadata

- **Status**: proposed
- **Date**: 2026-06-26
- **Decision Makers**: UACP maintainer
- **Consulted**: as-built `runtime-adapters/shared/guardian_pretooluse.py`; `docs/runtime/runtime-enforcement.md` (command-string inspection insufficiency); the worktree-protocol (Invariant #2) and checkpoint/diff evidence coverage (EXECUTE→VERIFY)
- **Informed**: all agents; hook/runtime-adapter authors
- **Related**: AGENTS.md Key Invariant #2 (no main writes) and #3 (governed writers only); `runtime-adapters/shared/README.md`

## Context and Problem Statement

The Guardian **PreToolUse hook** (`runtime-adapters/shared/guardian_pretooluse.py`) is a defense-in-depth shim for Claude Code / Kimi Code: it inspects a host tool call *before* it runs and can deny it. The MCP governed writers remain the authoritative containment; the hook is an extra boundary.

In a real Claude Code session the shim **over-blocked** and bricked the session — even with **no active UACP run** in the repo. Three root causes:

- **Wrong root resolution.** The shim called the kernel's `resolve_uacp_root()`, which — with `UACP_ROOT`/`HERMES_HOME` unset (the normal Claude Code case) — falls back to `~/.hermes/uacp`, a *different install*. The hook governed the wrong tree.
- **Over-broad policy.** The shim ran the full Guardian category model, which (a) demands governed-context fields (`uacp_run_id`/`policy_version`/`declared_authority`/…) that a raw host tool never carries, and (b) during an active run broadened to block **all** host writes/exec. The result: ordinary `Edit`/`Bash`/root-level writes were denied.
- The broad behavior also reached into territory that **Invariant #2** (worktree isolation) and **checkpoint/diff evidence** already own: it tried to block the agent's own *work-product* mutations, which is exactly the coding work the agent must do during EXECUTE.

There is also an ambiguity in **AGENTS.md Key Invariant #3** — "Governed writers only — No raw filesystem writes during a run." Read literally, that bans the agent from editing project code during EXECUTE, which is incoherent: a gate that blocks work-product edits blocks the work itself.

## Decision Drivers

- The hook's threat model is **only** *accidental corruption of governed state* — a raw host file write landing inside the governed `.uacp/` namespace. It is defense-in-depth, not a sandbox against hostile commands; container-grade isolation is explicitly out of scope.
- The MCP governed writers stay authoritative — the hook can fail open safely.
- The hook must never brick a session: ordinary edits, shell, and root-level writes must pass, with or without an active run.
- Invariant #3 must read coherently: govern *governed state*, not the agent's work-product.

## Considered Options

1. **Keep the full category model, patch the field requirements** — *rejected.* Still couples the host-tool path to governed-context fields a host tool never carries, and still broadens under a run. Fragile and over-scoped.
2. **Disable the hook entirely** — *rejected.* Loses the cheap, real protection against an accidental raw write into `.uacp/`.
3. **Narrow the shim to one self-contained predicate over `.uacp/`** — **chosen.**

## Decision Outcome

**Scope the host-tool path to a single narrow predicate**, self-contained in the shim (the shared `hook_kernel` is unchanged, so the Hermes adapter is unaffected):

> DENY iff the tool is a raw host mutating file tool (`Write` / `Edit` / `MultiEdit` / `NotebookEdit`) **and** its resolved target path is inside the governed namespace `<root>/.uacp/` (via `config.base_dir(root)`, traversal-safe containment). Otherwise ALLOW (exit 0, no stdout).

Concretely:
- **Root resolution** resolves the *project being worked in*: `UACP_ROOT` env → `CLAUDE_PROJECT_DIR` env (Claude Code sets it) → the payload `cwd` → the hook's own repo (last resort). It never falls back to `~/.hermes/uacp`.
- **No governed-context fields** are required; **Bash is not gated** (command-string inspection is insufficient — see `docs/runtime/runtime-enforcement.md`; a `bash echo > .uacp/x` redirect is the honest residual, acceptable under the accidental-corruption threat model); **root-level files** (e.g. `.mcp.json`) are not under `.uacp/` → allow; behavior is **identical** with or without an active run.
- The **governed MCP writers** (`mcp__uacp__uacp_*` → `uacp_*`) are not host file tools, so they are naturally allowed (the sanctioned write path). Spoofed-server defense is a hostile-actor concern, out of this hook's threat model — it remains the MCP server's job (and the kernel still refuses it on the Hermes path).
- Fail-OPEN is kept: malformed stdin or any internal error → exit 0, no stdout.

**Clarify AGENTS.md Key Invariant #3** to distinguish two write classes:
- **Governed-state writes** — the `.uacp/` namespace plus lifecycle/manifest artifacts — go through the governed writers during a run.
- **Work-product writes** — project code the agent edits during EXECUTE — are **not** raw-blocked. They are contained by the worktree (Invariant #2) and captured as evidence by checkpoint/diff coverage (EXECUTE→VERIFY).

### Positive Consequences

- The hook stops bricking sessions: ordinary edits, shell, and root-level writes pass.
- The remaining guard is exactly the threat it serves — accidental raw writes into `.uacp/`.
- Invariant #3 reads coherently; no overreach into Invariant #2 / checkpoint territory.
- The shim is self-contained and simple; `hook_kernel` and the Hermes adapter are untouched.

### Negative Consequences

- A `bash`-redirect into `.uacp/` bypasses the hook (the honest residual). Acceptable under the accidental-corruption threat model; real containment (deferred) needs process-level isolation, and the MCP writers remain authoritative.
- The hook no longer defends against a spoofed MCP server — by design; that defense lives in the MCP server and the kernel.

## Validation

- `tests/integration/test_pretooluse_hook.py` — narrow-predicate matrix (function-level via `main()` + subprocess): raw `Write`/`Edit`/`NotebookEdit` into `.uacp/` → DENY with an actionable, governed-writer-naming reason; ordinary project edit (run active and no run) → ALLOW; `Bash` touching `state/` → ALLOW; `Read` → ALLOW; root-level `.mcp.json` write → ALLOW (the session-bricking regression); wrong-root regression (governs `CLAUDE_PROJECT_DIR`, not `~/.hermes/uacp`); malformed/internal-error → fail open. The full suite stays green.

## Related ADRs

- Related: [ADR-0008](0008-doc-structure-and-adr-adoption.md) (documentation structure)

## References

- Implementation: `runtime-adapters/shared/guardian_pretooluse.py`
- Tests: `tests/integration/test_pretooluse_hook.py`
- Docs: `runtime-adapters/shared/README.md`; `docs/runtime/runtime-enforcement.md`
