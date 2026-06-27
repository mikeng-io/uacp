# Claude Code runtime adapter

Claude-Code-specific wiring for the UACP plugin. Two hooks register here, both
declared in this directory's manifest `runtime-adapters/claude/hooks.json`, which
the plugin manifest `.claude-plugin/plugin.json` loads via its explicit pointer
`"hooks": "./runtime-adapters/claude/hooks.json"` (CC honors the explicit pointer —
it does not require hooks.json at the plugin root):

| Hook | Surface | File |
|---|---|---|
| `SessionStart` | cognition injection (this dir) | `runtime-adapters/claude/inject_uacp_md.py` |
| `PreToolUse` | the shared Guardian shim | `runtime-adapters/shared/guardian_pretooluse.py --profile claude` |

The PreToolUse shim is **shared** (identical across runtimes) and is documented in
[`../shared/README.md`](../shared/README.md). Only the Claude-Code-specific
SessionStart injector lives here.

## SessionStart cognition injection (`inject_uacp_md.py`)

`inject_uacp_md.py` is the **cognition-layer enforcement surface** of the CMS
principle (comprehend → measure → serialize; see ADR-0018 and
`design/comprehend-measure-serialize/25-enforcement-surfaces.md`). It injects the
UACP coherence preamble (`UACP.md`, minus its HTML-comment header) as
`SessionStart` `additionalContext`, so a host agent inherits the discipline at
session start.

Like the Guardian shim it **fails open**: a missing *or undecodable* `UACP.md`
yields `exit 0` with no output and never blocks a session (it is a cognition nudge,
not a gate — the architecture surface is the fail-closed one). Stdlib only; it
imports nothing from the kernel.

It is **Claude-Code-only today**; Kimi / opencode would each need their own
session-start hook (a follow-up, analogous to the manual `config.toml` paste that
wires the PreToolUse shim on Kimi — see [`../kimi/README.md`](../kimi/README.md)).

## Install

Claude Code loads `runtime-adapters/claude/hooks.json` via the plugin manifest's
explicit pointer (`.claude-plugin/plugin.json` →
`"hooks": "./runtime-adapters/claude/hooks.json"`). CC's auto-discovery default is
`./hooks/hooks.json`, which we deliberately do not use — the explicit pointer makes
the by-runtime placement work (install-verified: `claude plugin validate --strict`
passes and a real install reports `Hooks (2) SessionStart, PreToolUse`). No manual
step is required once the plugin is installed. The two wired hooks are:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/runtime-adapters/claude/inject_uacp_md.py\"",
            "timeout": 10
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/runtime-adapters/shared/guardian_pretooluse.py\" --profile claude",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

For the marketplace / local-clone install flow and MCP server setup, see the
adapter map [`../README.md`](../README.md).
