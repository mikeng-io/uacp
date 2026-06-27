# Serena MCP — read-only LSP overlay

[Serena](https://github.com/oraios/serena) is the LSP-over-MCP layer UACP ships
with the plugin. It gives the agent live, workspace-bound symbol intelligence
(definitions, references, symbol overview) across 40+ languages. It is wired at the
**plugin level** (so installing the plugin brings it) — not just when the working
directory is `codeflair/`.

UACP runs Serena **read-only**: it is an *overlay the agent queries*, never an
editor. UACP performs edits through its own governed path; Serena's editing/shell
tools are deliberately excluded (see *Governance* below).

## Invocation

Registered in each runtime's plugin manifest `mcpServers` (Claude Code:
`.claude-plugin/plugin.json`; Kimi: `kimi.plugin.json`):

```
uvx --from git+https://github.com/oraios/serena serena start-mcp-server \
  --context <host> --mode planning --project-from-cwd --enable-web-dashboard false
```

| Flag | Why |
|---|---|
| `--context claude-code` (CC) / `--context ide` (Kimi) | Host-appropriate tool/prompt profile. `claude-code` is Serena's built-in context for Claude Code (per its client docs); Kimi has no dedicated context, so the generic `ide` profile is used. Verify names with `serena context list`. |
| `--mode planning` | **Read-only.** Serena's `planning` mode excludes *every* mutator — `create_text_file`, `replace_symbol_body`, `insert_after_symbol`, `insert_before_symbol`, `delete_lines`, `replace_lines`, `insert_at_line`, `execute_shell_command`, `replace_content` — while keeping the query tools (`find_symbol`, `find_referencing_symbols`, `get_symbols_overview`). |
| `--project-from-cwd` | Auto-activates the current workspace so symbol lookups work without manual project activation. Serena documents this flag as "intended for CLI-based agents like Claude Code, Gemini and Codex." |
| `--enable-web-dashboard false` | Serena's defaults are `web_dashboard: true` + `web_dashboard_open_on_launch: true`, i.e. it opens a **browser tab on every launch** and binds a dashboard port. For a plugin that starts Serena every session that is noise + port churn, so the bundled overlay runs headless. |

The official Claude Code setup (`serena start-mcp-server --context claude-code
--project-from-cwd`) is the baseline; `--mode planning` and
`--enable-web-dashboard false` are UACP-specific hardening on top.

## Governance — why read-only

Serena's mutators are **MCP tool calls**, which the UACP Guardian PreToolUse shim
(`runtime-adapters/shared/guardian_pretooluse.py`) does **not** intercept — that
shim only guards native `Write`/`Edit`/`MultiEdit`/`NotebookEdit`. So an
edit-capable Serena could write under `.uacp/` around the governed writers and
ledger. Running Serena in `--mode planning` removes that exposure **at the source**
(no mutator tools are offered). Extending the shim to also police MCP mutators is a
possible defense-in-depth follow-up, but read-only Serena is the primary control.

## Prerequisite — `uv`

Serena runs via `uvx`, so the user needs `uv`/`uvx` on PATH. It is **declared, not
auto-provisioned**; if `uv` is absent Serena simply does not load (the agent loses
the live LSP overlay but everything else works — graceful degrade).

## Per-runtime enablement

- **Claude Code** — registered in `.claude-plugin/plugin.json`; loads on plugin install.
- **Kimi** — registered in `kimi.plugin.json`, but Kimi starts plugin MCP servers
  only after they are enabled in a new session. Enable **both** servers:
  `/plugins mcp enable uacp uacp` and `/plugins mcp enable uacp serena` (see
  `runtime-adapters/kimi/README.md`).

## Relationship to Codeflair (consumption deferred)

Wiring Serena here gives the **agent** live LSP-over-MCP tools. It does **not** yet
make Codeflair *consume* Serena as its internal `"lsp"` edge source — Codeflair's
`SerenaOverlay` is a guarded stub, so Codeflair queries remain store-authoritative.
That internal-overlay integration is a separate, deferred piece.

## Verification

Confirmed against a real install: `claude plugin install` then `claude mcp list`
shows `plugin:uacp:serena … --context claude-code --mode planning --project-from-cwd
--enable-web-dashboard false  ✔ Connected`. Context names checked with
`serena context list`; the `planning` exclusions checked against Serena's
`resources/config/modes/planning.yml`; flags checked against
`serena start-mcp-server --help`. (`serena tools list` does not accept
`--context`/`--mode`, so the read-only tool set is config-verified, not runtime-dumped.)
