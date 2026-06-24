---
type: analysis
title: Codeflair — Delivery, Install & Toolchain
description: One core, four faces (lib · CLI · MCP · plugin) — "lighter than MCP." The install model — Codeflair is one binary; it auto-provisions the SCIP indexers (prebuilt, never `go install`); the language toolchain is present-for-your-own-code; LSP is discovered/provisioned and degrades gracefully (never dropped). Standalone, zero-UACP package; repo location reversible.
tags: [codeflair, delivery, install, packaging, cli, mcp, toolchain]
timestamp: 2026-06-24
edges:
  - {dst: 09-abstraction, rel: depends_on, provenance: asserted}
---

# Codeflair — Delivery, Install & Toolchain

## One core, four faces ("lighter than MCP")

The core engine (indexer + store + query) is exposed four ways — all thin wrappers, not reimplementations:

- **lib** — `import codeflair` (in-process)
- **CLI** — `codeflair index` / `codeflair query`
- **MCP server** — `query()` as an MCP tool, callable by any agent runtime (Claude Code, kimi, opencode)
- **plugin** — the runtime-specific shim

The point: **MCP is a *face*, not the substance.** Building an MCP server is ceremony; Codeflair is one
engine you consume however you like — so it's *lighter* than "stand up an MCP server." (CF-D9 packaging.)

## Install = install the plugin; the MCP comes *with* it (no separate MCP setup)

The whole point: the user installs **one plugin**, and every MCP it needs is **bundled and
auto-registered** — never "install this MCP, that MCP, the other MCP." The mechanism (Claude Code,
verified): **the plugin ships a `.mcp.json` at its root**; installing/enabling the plugin **auto-loads it**
— no `claude mcp add`, no user config. The plugin's `.mcp.json` declares **both Codeflair's own MCP and
Serena** (the LSP layer) — so one install brings the lot:

```json
// <plugin-root>/.mcp.json  — shipped IN the plugin, auto-registered on install
{ "mcpServers": {
    "codeflair": { "type": "stdio", "command": "codeflair", "args": ["mcp"] },
    "serena":    { "type": "stdio", "command": "uvx",
                   "args": ["--from","git+https://github.com/oraios/serena","serena","start-mcp-server"],
                   "env": { "MCP_TIMEOUT": "60000" } } } }
```
(Cross-runtime: same servers; only the registration file differs — `.mcp.json` for Claude Code, the
equivalent plugin/config block for Hermes/Kimi/opencode. One server set, N thin registration shims.)

**Hard truth:** precise code intel for language X *requires* X's toolchain (SCIP/LSP typecheck) — that's
intrinsic, not a Codeflair limit. **But it's free**, because anyone working on an X codebase already has
X's toolchain. `uv` (for Serena) is the one thing **left to the user** — declared, not auto-provisioned.
So the user installs **the plugin**:

```
brew install codeflair        # or curl | sh — ONE thing
codeflair index               # auto-fetches scip-go (prebuilt), runs it using your existing Go
codeflair query Pool.Conn
```

| User installs | Codeflair provides | Already present (your code) | Never required |
|---|---|---|---|
| `codeflair` (1 binary) | SQLite, the **SCIP indexers** (auto-fetched) | the language toolchain | LSP servers, manual setup |

- **SCIP indexers auto-provisioned** — Codeflair downloads the **prebuilt release binary** into
  `~/.codeflair/bin/` (prefer **prebuilt release binaries** over `go install` for reproducibility — and
  because the spike hit real `go install` breakage: stale/relocated module paths, replace-directive errors).
- **LSP = Serena, declared in the bundled `.mcp.json` (DECIDED).** Don't hand-integrate N language
  servers — **Serena** (MCP, 40+ langs) is the LSP layer, shipped in the plugin's `.mcp.json` via `uvx`.
  It is the freshness half of the SCIP⊕LSP reconcile ([10-freshness](10-freshness.md)) — **not "optional
  by design."** **`uv`/`uvx` is the user's responsibility:** we do *not* auto-provision it or build a
  degrade path. If the user hasn't set up `uv`, Serena just doesn't load (they lose the live LSP overlay;
  SCIP/tree-sitter/grep still work) — a user config gap, not a feature.
- **No toolchain for a language → that language degrades to grep + tree-sitter**, with a message — never
  blocks install (the tree-sitter breadth floor, [02-probes](02-probes.md)).

## Product language — Python (DECIDED)

Performance is language-agnostic (SCIP + SQLite do the work), so the choice is about **integration + build
speed**, not perf. **Python is the product language:** it adopts **Serena** (Python) for LSP natively,
matches the **MCP Python SDK** + UACP's kernel, and is fastest to build. The single-Go-binary "portable
execution" option is **dropped** — the plugin ships a Python MCP + Serena via `.mcp.json`/`uvx`, and `uv`
is the user's responsibility. *(Superseded note — earlier this section argued Go for a single binary;
Python won on native Serena/MCP integration + velocity.)* Python was also the spike
language only. Rust only if max-perf is later wanted.

## Packaging boundary (CF-D12)

The invariant is a **standalone, zero-UACP, independently-installable package** (lib+CLI+MCP) — a CI lint
enforces "no UACP import in core." **Repo location is reversible:** start as an in-repo package (low
friction), extract to its own repo when external adoption / independent release cadence demands. The
boundary, not the repo, is what makes it a standalone plugin.
