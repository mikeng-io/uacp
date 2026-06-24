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

## The install model — the host installs only Codeflair

**Hard truth:** precise code intel for language X *requires* X's toolchain (SCIP/LSP typecheck) — that's
intrinsic, not a Codeflair limit. **But it's free**, because anyone working on an X codebase already has
X's toolchain. So the user installs **only Codeflair (one binary)**:

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
  A Go build can **embed `scip-go` in-process** → zero external dep for Go.
- **LSP is discovered/provisioned, never dropped** — it's the freshness half of the SCIP⊕LSP reconcile
  ([10-freshness](10-freshness.md)). Present → full reconcile; **absent → degrade** (single-file SCIP
  re-index, or grep+stale-flag), clearly flagged. A *fallback*, never silent removal, never "set up
  servers first." **Adopt the multi-LSP layer, don't hand-integrate N servers** (CF-D14): **Serena**
  (MCP, 40+ langs) or **multilspy** (embeddable library) already abstract the per-server lifecycle/quirks
  — Codeflair uses one of them as its LSP backend. *(Note: adopting Serena leans the core toward Python or
  a sidecar — a real coupling vs. the single-Go-binary goal; decide consciously.)*
- **No toolchain for a language → that language degrades to grep + tree-sitter**, with a message — never
  blocks install (the tree-sitter breadth floor, [02-probes](02-probes.md)).

## Product language (decided by the delivery goal, not perf)

Performance is language-agnostic (SCIP + SQLite do the work). The choice is about **distribution**:
**Go** is the product home — single static binary (the "portable execution" goal), **SCIP-ecosystem-native**
(scip-go/scip are Go; can embed scip-go), dogfoods (Trustless is Go), maintainable. Python is the spike
language only. Rust only if max-perf is later wanted.

## Packaging boundary (CF-D12)

The invariant is a **standalone, zero-UACP, independently-installable package** (lib+CLI+MCP) — a CI lint
enforces "no UACP import in core." **Repo location is reversible:** start as an in-repo package (low
friction), extract to its own repo when external adoption / independent release cadence demands. The
boundary, not the repo, is what makes it a standalone plugin.
