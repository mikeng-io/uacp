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

**Claude Code** (`.claude-plugin/plugin.json`) — full lock-down via a shipped mode:
```
uvx --from git+https://github.com/oraios/serena serena start-mcp-server \
  --context agent \
  --mode ${CLAUDE_PLUGIN_ROOT}/runtime-adapters/serena-readonly.yml \
  --project-from-cwd --enable-web-dashboard false
```

**Kimi** (`kimi.plugin.json`) — best-effort via built-in modes (see caveat):
```
uvx … serena start-mcp-server \
  --context agent --mode planning --mode no-memories \
  --project-from-cwd --enable-web-dashboard false
```

| Flag | Why |
|---|---|
| `--context agent` | The **minimal**, non-steering context (~36-char prompt). The "official" `claude-code` context injects a large prompt that *forbids* native Read/Edit and pushes Serena's editing tools — it hijacks the host agent and contradicts our read-only setup, so we do **not** use it. |
| `--mode <serena-readonly.yml>` (CC) | A **custom read-only mode** shipped in the repo: empty prompt + `excluded_tools` covering **every** mutator including `rename_symbol`/`safe_delete_symbol` (which *no* built-in mode excludes) and Serena's memory/onboarding tools. Referenced by **absolute** path via `${CLAUDE_PLUGIN_ROOT}` (committed files ship with the plugin / git clone), so there is no provisioning step and no cwd collision with `--project-from-cwd`. |
| `--mode planning --mode no-memories` (Kimi) | Modes compose (`--mode` is repeatable). Built-in fallback because Kimi has no plugin-root variable and a *relative* mode-file path collides with `--project-from-cwd`. `planning` = read-only editing set; `no-memories` = drops memory/onboarding. **Caveat:** built-ins cannot exclude `rename_symbol`/`safe_delete_symbol`, so those two remain on Kimi (documented gap), and the Kimi entry is **unverified** (no Kimi install to test). |
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

## Prerequisite — `uv`

Serena runs via `uvx`, so the user needs `uv`/`uvx` on PATH. It is **declared, not
auto-provisioned**; if absent, Serena simply does not load (graceful degrade — the
agent loses the live LSP overlay, nothing else breaks).

## Per-runtime status

- **Claude Code** — full read-only lock-down (custom mode), install-verified
  (`claude mcp list` → `plugin:uacp:serena … ✔ Connected`).
- **Kimi** — best-effort (`planning` + `no-memories`); `rename_symbol` /
  `safe_delete_symbol` remain and the entry is unverified. Enable **both** servers
  in a new session: `/plugins mcp enable uacp uacp` and
  `/plugins mcp enable uacp serena` (see `kimi/README.md`).
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
