# Shared runtime-adapter logic — the PreToolUse Guardian shim

This directory holds the **cross-runtime** adapter logic: code that is identical
across host runtimes and is reused by their per-runtime wiring. Today that is the
UACP Guardian **PreToolUse hook companion** — a CLI shim that lets a host
(Claude Code, Kimi Code, …) enforce Guardian policy *before* a tool runs, without
going through the Hermes runtime.

The shim lives at `runtime-adapters/shared/guardian_pretooluse.py`. It is a thin,
self-contained `.uacp/` guard — it does **not** share the broad Guardian category
model with the Hermes adapter. (The shared kernel
`skills/uacp-core/scripts/hook_kernel.py` → `evaluate_pre_tool_call` is unchanged
and still drives the Hermes `uacp_guardian` plugin; the shim no longer calls it.)

It is profile-parameterized — `--profile {claude,kimi}` is accepted for invocation
compatibility but no longer changes the predicate, because the host tool names it
guards (`Write` / `Edit` / `MultiEdit` / `NotebookEdit`) are identical across the
runtimes that drive UACP through bare host tools. That sameness is exactly why the
shim lives in `shared/` rather than in a per-runtime directory.

## Threat model: accidental corruption of governed state only

> **The MCP server's governed handlers remain the authoritative containment.**

The governed writers (`uacp_state_write`, `uacp_doc_write`, …) own the actual
filesystem mutations and perform their own path-bounded containment inside the MCP
server (`runtime-adapters/mcp/uacp_mcp_server.py`). This hook serves **one** narrow
threat: *accidental corruption of governed state* — a raw host file write that
lands inside a governed `.uacp/` namespace (the main repo's **or** any worktree's).
It is defense-in-depth, **not** a sandbox against hostile commands, and container-
grade isolation is explicitly out of scope. Because the MCP handlers are
authoritative, the hook can safely **fail open** (see D1) — a hook that crashes
never opens a writer that the MCP server would have refused.

## The predicate (target-relative, worktree-robust)

> DENY iff the tool is a raw host mutating file tool (`Write` / `Edit` /
> `MultiEdit` / `NotebookEdit`) **and** any **ancestor directory** of the resolved
> target path is named `.uacp` (compared casefolded). Otherwise ALLOW (exit 0, no
> stdout).

The decision is **target-relative**: it inspects the path being written, not a
single resolved "project root". This is what makes it worktree-safe — a write into
`<repo>/.worktrees/X/.uacp/...` (that worktree's own governed state) is denied just
like `<repo>/.uacp/...`, with no root resolution. A **relative** target path is
resolved against the payload `cwd` (the tree the agent is in — the worktree when
working inside one), never the hook process cwd.

Consequences (each is intentional — see ADR-0019):

- **Bash is ENTIRELY ungated.** Command-string inspection is insufficient to know
  what a shell command writes (see `docs/runtime/runtime-enforcement.md`), so the
  hook does not gate the shell at all. **Any** shell-driven write therefore
  bypasses it — not only a redirect (`> .uacp/x`), but equally `cp`/`mv`/`tee`,
  `sed -i`, an interpreter `open()`, `git checkout`, and so on. This is the honest
  residual, acceptable under the accidental-corruption threat model: the MCP
  governed writers and the worktree are the real containment (process-level
  isolation is deferred).
- **Raw project edits are not blocked.** Work-product writes (project code the
  agent edits during EXECUTE) are contained by the worktree (Invariant #2) and
  captured as evidence by checkpoint/diff coverage (EXECUTE→VERIFY) — see the
  clarified AGENTS.md Key Invariant #3 and ADR-0019. A gate that blocked the
  agent's own work-product would block the coding work itself.
- **No root-touch block.** A file at the repo root (e.g. `.mcp.json`) has no
  `.uacp` ancestor, so it is allowed. (Over-blocking root-level writes is what
  bricked a real session.) A file literally **named** `.uacp` (or `*.uacp`) as the
  leaf is allowed too — only writing *into* a `.uacp/` directory is blocked.
- **Case-insensitive FS safe.** The `.uacp` component is matched casefolded, so a
  `.UACP/` write on macOS/NTFS (where it is the same directory) is still denied.
- **Run-state-independent.** The decision is identical whether or not a run is
  active — no governed-context fields are required of a host tool.
- **MCP writers pass.** The governed `mcp__uacp__uacp_*` (→ `uacp_*`) tools are
  not host file tools, so the predicate naturally allows them — they are the
  sanctioned write path. Spoofed-MCP-server defense is a hostile-actor concern,
  out of this hook's threat model; it remains the MCP server's and the kernel's
  job.

## How membership is decided (no project-root resolution)

The membership decision needs **no** single "project root": it walks the resolved
target's ancestor directories and denies iff one is named `.uacp` (casefolded).
This deliberately drops the earlier root-resolution scheme (which resolved one
project root and checked `target under <root>/.uacp/`) because that missed the
**worktree** case — a write into `<repo>/.worktrees/X/.uacp/` resolves *outside*
`<repo>/.uacp/` and would slip through, even though that worktree's `.uacp/` is the
active run's governed state.

The only context used is the payload `cwd`, and only to resolve a **relative**
target path (against the tree the agent is in). The shim reads **no** lifecycle
phase and **no** governed-context fields: the predicate is run-state-independent.

## Per-runtime wiring (where this shim is registered)

The shim is shared; *how a runtime invokes it* is per-runtime and lives in the
runtime's own directory:

- **Claude Code** — auto-bundled via `hooks/hooks.json` (plugin root). See
  [`../claude/README.md`](../claude/README.md).
- **Kimi Code** — one-time manual `~/.kimi-code/config.toml` paste (Kimi's plugin
  manifest ignores a `hooks` field). See [`../kimi/README.md`](../kimi/README.md).
- **Codex** — no PreToolUse hook surface today → MCP-governed-only. See
  [`../codex/README.md`](../codex/README.md).

## Settled design decisions

- **D1 — Fail OPEN.** Malformed/unparseable stdin or any unexpected internal
  exception results in `exit 0` with **no stdout** (allow) and a warning on
  stderr. Safe because the MCP governed handlers remain authoritative — failing
  open in the hook never opens a writer.
- **D5 — Deny holds under `bypassPermissions`.** A `deny` is emitted regardless of
  the payload's `permission_mode`. The shim never short-circuits to allow on
  `permission_mode == "bypassPermissions"`.
- **D6 — Defense-in-depth.** The hook augments — it does not replace — the
  authoritative MCP governed handlers.

> Historical note: earlier revisions ran the full Guardian category model with
> tool-name normalization and per-phase admissibility (the old D2–D4). That
> over-blocked ordinary edits, shell, and root-level writes and bricked sessions;
> ADR-0019 narrowed the shim to the single `.uacp/` predicate above.

## Output contract

| Decision | Behavior |
|---|---|
| block | `exit 0` + stdout `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"<reason>"}}` (+ stderr reason). The reason is actionable — it names the blocked tool, the `.uacp/` target, and a governed writer to use instead. If the stdout write fails, `exit 2` + stderr. |
| allow | `exit 0`, **no stdout**. |
| malformed / crash | `exit 0`, **no stdout**, stderr warning (D1). |

## No new dependencies

The shim uses only the Python standard library. It does **not** import `mcp`, and
no longer imports `core` / `hook_kernel` / `engines.io`.
