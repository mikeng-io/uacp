# Claude Code / Kimi Code PreToolUse Guardian Hook

This guide documents the UACP Guardian **PreToolUse hook companion** — a CLI shim
that lets Claude Code and Kimi Code enforce Guardian policy *before* a tool runs,
without going through the Hermes runtime.

The shim lives at `runtime-adapters/hooks/guardian_pretooluse.py`. It shares its
decision logic with the Hermes adapter via the runtime-neutral kernel
(`skills/uacp-core/scripts/hook_kernel.py` → `evaluate_pre_tool_call`), which is
the same code path the Hermes `uacp_guardian` plugin uses.

## Defense-in-depth, not the authority

> **The MCP server's governed handlers remain the authoritative containment.**

The governed writers (`uacp_state_write`, `uacp_doc_write`, …) own the actual
filesystem mutations and perform their own path-bounded containment inside the MCP
server (`runtime-adapters/mcp/uacp_mcp_server.py`). This hook is an *additional*
boundary: it adds pre-call enforcement for runtimes that drive UACP through the
bare MCP tools, and it stops a raw host `Write`/`Bash` from scribbling into the
governed `.uacp/` namespace before the call is even dispatched. Because the MCP
handlers are authoritative, the hook can safely **fail open** (see D1) — a hook
that crashes never opens a writer that the MCP server would have refused.

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

## Environment contract

The shim resolves the UACP root and the active lifecycle phase from the
environment, degrading gracefully when nothing is set:

| Variable | Role |
|---|---|
| `UACP_ROOT` | The UACP root (repo). Falls back to `HERMES_HOME/uacp`, then `~/.hermes/uacp` (see `resolve_uacp_root`). |
| `UACP_RUN_ID` | Active run id. Read **first** for phase resolution. |
| `UACP_PHASE` | Active lifecycle phase. Read **first** for phase resolution. |

**Phase source (D4):** the shim reads `UACP_RUN_ID`/`UACP_PHASE` from the
environment first. If neither is set, it falls back to reading
`<root>/.uacp/state/current.yaml#active_run_id` and `#active_run_manifest`, then
that manifest's `current_phase`. Every file read is defensive: a missing or
unreadable `current.yaml`/manifest yields empty run/phase (no crash) and the run
is treated as inactive.

## Tool-name normalization

A host runtime names its tools `Read`/`Bash`/`Edit`/… and namespaces MCP tools as
`mcp__<server>__<tool>` (Claude Code) or `mcp_<server>_<tool>` (Hermes). The raw
Guardian kernel knows none of those names — so, during an active run, they would
fall through to `external.unknown_mutator` (a protected category) and be blocked,
bricking the agent's read tools. The shim therefore **normalizes** the host tool
name to a kernel tool name before classification (`hook_kernel.normalize_tool_name`),
driven by `config/uacp.toml [guardian.host_tool_classification.<profile>]`:

| Host tool | Kernel tool | Guardian category | Default decision |
|---|---|---|---|
| `Read`, `Grep`, `Glob`, `LS`, `NotebookRead` | `read_file` | `read.local` | allow |
| `Bash`, `BashOutput`, `KillBash` | `terminal` | `exec.shell` | block_pending_heartgate |
| `Edit`, `Write`, `MultiEdit`, `NotebookEdit` | `write_file` | `file.write` | require_approval |
| `WebFetch` | `web_fetch` | `external.network_read` | allow_with_audit |
| `WebSearch` | `web_search` | `external.network_read` | allow_with_audit |

MCP namespacing is stripped: a recovered `uacp_*` tool known to the kernel (e.g.
`mcp__uacp__uacp_state_write` → `uacp_state_write`) is classified as its real
governed category; any other MCP tool is left namespaced so it classifies as
`runtime.extension`. Unmapped host names pass through unchanged.

## Security decisions

These are the settled design decisions the shim implements.

- **D1 — Fail OPEN.** Malformed/unparseable stdin, or any unexpected internal
  exception, results in `exit 0` with **no stdout** (allow) and a warning on
  stderr. Safe because the MCP governed handlers remain authoritative — failing
  open in the hook never opens a writer.
- **D2 — Raw edits DEFER.** Host `Edit`/`Write`/`MultiEdit`/`NotebookEdit` map to
  the kernel `file.write` category, whose default is `require_approval` — *not* a
  block — so ordinary project edits pass through to the runtime's normal approval
  prompt and the EXECUTE phase keeps working. The kernel still **hard-blocks**
  writes whose target path is under the governed `.uacp/` namespace via its
  existing direct-write / root-touch rules. Raw edits are deliberately **not**
  mapped to `external.unknown_mutator`. To avoid a host runtime's repo-root `cwd`
  (which, for a UACP-governed repo, *is* the UACP root) making every ordinary edit
  look UACP-bound, the shim binds `workspace` to the *parent directory of the
  target path*, not the process cwd — so a `.uacp/` target still binds and blocks,
  while a project-file edit outside `.uacp/` defers.
- **D3 — Policy-load failure.** Mirrors Hermes `_block_for_policy_error`: bare
  read tools (`Read`/`Grep`/`Glob`/`LS`/`NotebookRead`, kernel `read_file`/
  `search_files`) are allowed; every other (governed-looking) call is denied.
- **D4 — Phase source.** Environment first, `current.yaml` → manifest fallback,
  graceful degradation (documented above).
- **D5 — Deny holds under `bypassPermissions`.** A Guardian `deny` is emitted
  regardless of the payload's `permission_mode`. The shim never short-circuits to
  allow on `permission_mode == "bypassPermissions"`.
- **D6 — Defense-in-depth.** As stated above, the hook augments — it does not
  replace — the authoritative MCP governed handlers.

## Output contract

| Decision | Behavior |
|---|---|
| block | `exit 0` + stdout `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"<reason>"}}` (+ stderr reason). If the stdout write fails, `exit 2` + stderr. |
| allow / allow_with_audit / require_approval (defer) | `exit 0`, **no stdout**. |
| malformed / crash | `exit 0`, **no stdout**, stderr warning (D1). |

## No new dependencies

The shim and kernel use only the Python standard library plus the existing UACP
kernel (`core`, `config`, `hook_kernel`, `engines.io`, and optionally PyYAML for
the phase fallback). The shim does **not** import `mcp`.

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
