# Serena MCP — read-only LSP overlay

[Serena](https://github.com/oraios/serena) is the LSP-over-MCP layer UACP ships
with the plugin: live, workspace-bound symbol intelligence (definitions,
references, implementations, symbol overview, diagnostics) across 40+ languages.
It is wired at the **plugin level** (installing the plugin brings it), not only
when the working directory is `codeflair/`.

**Serena is not a pure LSP** — it is a coding-*agent* toolkit (symbol tools **plus**
editing, shell, memory, onboarding) that also injects a *system prompt* via the MCP
`instructions` field (assembled from its context + modes). UACP wants only the
**read-only symbol/diagnostic tools** and **none** of the prompt or mutators, so
the wiring below strips Serena down to a quiet read-only overlay. (Serena's other
capabilities are either unwanted for governance — editing/shell/refactor — or
redundant with UACP's own, *governed* systems — memory↔Oracle/handoffs,
onboarding↔TRIAGE, grep↔codeflair.)

## Invocation

Registered in each runtime's plugin manifest `mcpServers`.

Serena is **pinned to `@v1.5.3`** (not floating `main`) — required for the allowlist
below to stay correct and to avoid silently pulling new tools.

**Claude Code** (`.claude-plugin/plugin.json`) — fail-closed allowlist via a shipped mode:
```
uvx --from git+https://github.com/oraios/serena@v1.5.3 serena start-mcp-server \
  --context agent \
  --mode ${CLAUDE_PLUGIN_ROOT}/runtime-adapters/serena-readonly.yml \
  --project-from-cwd --enable-web-dashboard false
```

Serena is **not** wired for Kimi or Hermes (see *Per-runtime status*).

| Flag | Why |
|---|---|
| `--context agent` | The **minimal**, non-steering context (~36-char prompt). The "official" `claude-code` context injects a large prompt that *forbids* native Read/Edit and pushes Serena's editing tools — it hijacks the host agent and contradicts our read-only setup, so we do **not** use it. |
| `--mode <serena-readonly.yml>` (CC) | A **custom read-only mode** shipped in the repo using **`fixed_tools` (an ALLOWLIST), not `excluded_tools`**. Only six tools are ever exposed — `find_symbol`, `find_declaration`, `find_implementations`, `find_referencing_symbols`, `get_symbols_overview`, `get_diagnostics_for_file`. This is **fail-closed**: every mutator, refactor (`rename_symbol`/`safe_delete_symbol`), shell, memory/onboarding, **`activate_project`**, and file-read/grep tool is excluded by *omission*, and a tool added in a future Serena release cannot slip in (the reason a denylist failed review). Referenced by **absolute** path via `${CLAUDE_PLUGIN_ROOT}` (committed files ship via git clone), so no provisioning and no cwd collision with `--project-from-cwd`. |
| `--project-from-cwd` | Auto-activates the current workspace; Serena documents it as "intended for CLI-based agents like Claude Code, Gemini and Codex." |
| `--enable-web-dashboard false` | Serena defaults `web_dashboard` + `open_on_launch` both **true** → it opens a browser tab + binds a port on every launch. A plugin starts Serena every session, so it runs headless. |

## Governance — why read-only matters

Serena's mutators are **MCP tool calls**, which the UACP Guardian PreToolUse shim
(`runtime-adapters/shared/guardian_pretooluse.py`) does **not** intercept (it only
guards native `Write`/`Edit`/`MultiEdit`/`NotebookEdit`). An edit-capable Serena
could therefore write under `.uacp/` around the governed writers and ledger.
Removing the mutators at the source (read-only mode) closes that exposure;
`memory`/`onboarding` are excluded for the same reason (they create ungoverned
`.serena/memories/*`).

**Known limitation (cosmetic).** Serena's `base_modes` default to `interactive` +
`editing` and live in `~/.serena/serena_config.yml`; `--mode` overrides only
`default_modes`, and there is no CLI flag for base modes. So the `editing` base
mode's *prompt* still appears in Serena's MCP instructions ("use `replace_symbol_body`
…"). This is **inert**: the `fixed_tools` allowlist removes those edit tools, so the
agent cannot act on it — it's contradictory prompt text, not a capability. Clearing
it would require relocating Serena's whole home via `SERENA_HOME` (which moves its
runtime state too), not worth it for inert text.

## Prerequisite — `uv`

Serena runs via `uvx`, so the user needs `uv`/`uvx` on PATH. It is **declared, not
auto-provisioned**; if absent, Serena simply does not load (graceful degrade — the
agent loses the live LSP overlay, nothing else breaks).

## Per-runtime status

- **Claude Code** — full read-only lock-down via the `fixed_tools` allowlist (6
  tools), Serena pinned `@v1.5.3`, install-verified (`claude mcp list` →
  `plugin:uacp:serena … --mode …/serena-readonly.yml … ✔ Connected`).
- **Kimi** — **deferred.** Built-in modes can't exclude `rename_symbol` /
  `safe_delete_symbol` / `activate_project`, and Kimi has no plugin-root variable to
  reference the `fixed_tools` mode file cleanly (its relative path collides with
  `--project-from-cwd`). Rather than ship a leaky, unverified overlay, Serena is not
  wired for Kimi until the `fixed_tools` mode can be delivered fail-closed.
- **Hermes** — **deferred.** `runtime-adapters/hermes/` uses native Python plugins,
  not MCP registration, so Serena is not wired there; it would need Hermes's own
  MCP-client mechanism. Out of scope for now.

## Relationship to Codeflair (consumption deferred)

This gives the **agent** live LSP-over-MCP tools. It does **not** yet make Codeflair
*consume* Serena as its `"lsp"` edge source — `SerenaOverlay` is a guarded stub, so
Codeflair queries remain store-authoritative. That internal-overlay integration is a
separate, deferred piece.

## Verification

Confirmed against a real install: `claude plugin install` then `claude mcp list`
shows the full command with `--context agent --mode …/serena-readonly.yml … ✔
Connected`. Context names checked with `serena context list`; flags with
`serena start-mcp-server --help`; the exclusion set authored from the mode-YAML
schema (`description` / `prompt` / `excluded_tools` / `included_optional_tools`).
`serena tools list` does not accept `--mode`, so the read-only tool set is
config-verified against the shipped `serena-readonly.yml`, not runtime-dumped.
