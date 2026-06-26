# Claude Code / Kimi Code PreToolUse Guardian Hook

This guide documents the UACP Guardian **PreToolUse hook companion** — a CLI shim
that lets Claude Code and Kimi Code enforce Guardian policy *before* a tool runs,
without going through the Hermes runtime.

The shim lives at `runtime-adapters/hooks/guardian_pretooluse.py`. It is a thin,
self-contained `.uacp/` guard — it does **not** share the broad Guardian category
model with the Hermes adapter. (The shared kernel
`skills/uacp-core/scripts/hook_kernel.py` → `evaluate_pre_tool_call` is unchanged
and still drives the Hermes `uacp_guardian` plugin; the shim no longer calls it.)

## Threat model: accidental corruption of governed state only

> **The MCP server's governed handlers remain the authoritative containment.**

The governed writers (`uacp_state_write`, `uacp_doc_write`, …) own the actual
filesystem mutations and perform their own path-bounded containment inside the MCP
server (`runtime-adapters/mcp/uacp_mcp_server.py`). This hook serves **one** narrow
threat: *accidental corruption of governed state* — a raw host file write that
lands inside the governed `.uacp/` namespace. It is defense-in-depth, **not** a
sandbox against hostile commands, and container-grade isolation is explicitly out
of scope. Because the MCP handlers are authoritative, the hook can safely **fail
open** (see D1) — a hook that crashes never opens a writer that the MCP server
would have refused.

## The narrow predicate

> DENY iff the tool is a raw host mutating file tool (`Write` / `Edit` /
> `MultiEdit` / `NotebookEdit`) **and** its resolved target path is inside the
> governed namespace `<root>/.uacp/`. Otherwise ALLOW (exit 0, no stdout).

Consequences of the narrow scope (each is intentional — see ADR-0019):

- **Bash is not gated.** Command-string inspection is insufficient to decide
  what a shell command touches (see `docs/runtime/runtime-enforcement.md`), so
  the hook does not try. A `bash echo > .uacp/x` redirect therefore bypasses the
  hook — the honest residual, acceptable under the accidental-corruption threat
  model (real containment needs process-level isolation, deferred; the MCP
  writers stay authoritative).
- **Raw project edits are not blocked.** Work-product writes (project code the
  agent edits during EXECUTE) are contained by the worktree (Invariant #2) and
  captured as evidence by checkpoint/diff coverage (EXECUTE→VERIFY) — see the
  clarified AGENTS.md Key Invariant #3 and ADR-0019. A gate that blocked the
  agent's own work-product would block the coding work itself.
- **No root-touch block.** A file at the repo root (e.g. `.mcp.json`) is not
  under `.uacp/`, so it is allowed. (Over-blocking root-level writes is what
  bricked a real session.)
- **Run-state-independent.** The decision is identical whether or not a run is
  active — no governed-context fields are required of a host tool.
- **MCP writers pass.** The governed `mcp__uacp__uacp_*` (→ `uacp_*`) tools are
  not host file tools, so the predicate naturally allows them — they are the
  sanctioned write path. Spoofed-MCP-server defense is a hostile-actor concern,
  out of this hook's threat model; it remains the MCP server's and the kernel's
  job.

## Install

### Claude Code

Claude Code auto-discovers `hooks/hooks.json` at the plugin root, and the plugin
manifest (`.claude-plugin/plugin.json`) also references it explicitly via
`"hooks": "./hooks/hooks.json"`. No manual step is required once the plugin is
installed. The wired hook is:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/runtime-adapters/hooks/guardian_pretooluse.py\" --profile claude",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Kimi Code

The Kimi plugin (skills + the MCP governed-tools server) installs natively from
GitHub — see [the adapter README](../README.md#kimi-code). Kimi's plugin manifest
ignores a `hooks` field, so the enforcement hook **cannot** ship inside the
plugin; it is a **one-time manual edit** to `~/.kimi-code/config.toml`. Add this
`[[hooks]]` block, replacing `<abs>` with the absolute path to your clone:

```toml
[[hooks]]
event = "PreToolUse"
matcher = "*"
command = "python3 <abs>/runtime-adapters/hooks/guardian_pretooluse.py --profile kimi"
timeout = 10
```

Then start a new session (`/new`). There is no install script — this is a single
documented paste, by design (the gate can't ride in the plugin).

## Root resolution (DEFECT A)

The shim resolves the **project being worked in** — where `.uacp/` actually
lives — never the kernel default `~/.hermes/uacp`. Resolution order:

| Source | Role |
|---|---|
| `UACP_ROOT` env | Explicit root, honored first. |
| `CLAUDE_PROJECT_DIR` env | The project dir Claude Code sets per session. |
| payload `cwd` | The runtime's working directory for the call. |
| the hook's own repo root | Last resort (`Path(__file__).parents[2]`). |

The governed base is then `config.base_dir(root)` (default `<root>/.uacp`, honoring
a `[paths] base` override). The shim deliberately does **not** call the kernel's
`resolve_uacp_root()`, because with `UACP_ROOT`/`HERMES_HOME` unset (the normal
Claude Code case) that falls back to `~/.hermes/uacp` — a different install — and
the hook would govern the wrong tree.

The shim reads **no** lifecycle phase and **no** governed-context fields: the
narrow predicate is run-state-independent.

## Settled design decisions

- **A — Resolve the project root.** As above: `UACP_ROOT` → `CLAUDE_PROJECT_DIR`
  → payload `cwd` → the hook's own repo; never `~/.hermes/uacp`.
- **D1 — Fail OPEN.** Malformed/unparseable stdin, an unresolvable governed base,
  or any unexpected internal exception results in `exit 0` with **no stdout**
  (allow) and a warning on stderr. Safe because the MCP governed handlers remain
  authoritative — failing open in the hook never opens a writer.
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

The shim uses only the Python standard library plus `config.base_dir` from the
existing UACP kernel (for the `[paths] base`-aware governed namespace). It does
**not** import `mcp`, and no longer imports `core` / `hook_kernel` / `engines.io`.

## Companion hook: SessionStart cognition injection

A second, independent hook lives beside this one: `runtime-adapters/hooks/inject_uacp_md.py`,
registered as a `SessionStart` hook in the same `hooks/hooks.json`. It injects the UACP coherence
preamble (`UACP.md`, minus its HTML-comment header) as `SessionStart` `additionalContext` — the
**cognition-layer enforcement surface** of the CMS principle (see ADR-0018 and
`design/comprehend-measure-serialize/25-enforcement-surfaces.md`). Like the Guardian shim it
**fails open**: a missing *or undecodable* `UACP.md` yields `exit 0` with no output and never blocks a
session (it is a cognition nudge, not a gate — the architecture surface is the fail-closed one). It is
**Claude-Code-only today**; Kimi/opencode would each need their own session-start hook (a follow-up,
analogous to the manual `config.toml` paste above). Stdlib only; imports nothing from the kernel.
