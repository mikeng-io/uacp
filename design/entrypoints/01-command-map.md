---
type: reference
title: The Command Map — every script → `uacp <cmd>`, classified, + the build plan
description: >-
  The concrete target: every standalone scripts/*.py + the 11 governed tools mapped to a single
  `uacp <command>` surface, classified by command class (§1 — by mutation, not "dev-ness"), with
  the registry-generalization + incremental migration plan. Build deferred until after Phase C.
tags: [uacp, entry-points, cli, command-map, migration, build-plan]
timestamp: 2026-06-23
edges:
  - {dst: 00-unified-entrypoints, rel: depends_on, provenance: asserted}
---

# The Command Map

Grounded in the as-built inventory (`scripts/` = 12 files; `tool_specs.py` = 11 governed tools).

## 1. Every entry point → `uacp <cmd>` (classified per node 00 §3)

| Today | `uacp` command | Class | Notes |
|---|---|---|---|
| `tool_specs.py` — **8 mutating** writers/state tools | `uacp tool <name>` (or top-level) | governed-mutating | already MCP-exposed; CLI = the second adapter |
| `tool_specs.py` — **3 read-only** (`uacp_sandbox_check`, `uacp_heartgate_check`, `uacp_oracle_query`, already `read_only=True`) | `uacp <name>` | read/validate | already MCP-exposed; not mutators |
| `scripts/validate_uacp_artifacts.py` | `uacp lint [--kind …]` | read/validate | the node-33 transform → uacp-lint (shape delegates to schema.py; referential stays) |
| *(net-new, D8)* | `uacp fmt` | read/validate | the uacp-fmt canonicalizer sibling (one skill, two subcommands) |
| `scripts/phase0_verify.py … phase4_verify.py` | `uacp verify [--phase N]` (or `uacp selfcheck`) | read/validate | the slice phase verifiers; CI-facing |
| `scripts/check_active_uacp_skill_links.py` | `uacp check skill-links` | read/validate | CI lint |
| `scripts/import_loader_verify.py` | `uacp check imports` | read/validate | CI lint |
| `scripts/migrate_knowledge_corpus.py` | `uacp migrate knowledge-corpus` | **operator-mutating** | mutates (`shutil.move` files) → **audit required**; CLI-only, not MCP |
| `scripts/migrate_to_uacp_dir.py` | `uacp migrate uacp-dir` | **operator-mutating** | mutates (`rename` dirs, rewrite `.gitignore`/config) → **audit required**; CLI-only |
| `scripts/oracle_reranker_bakeoff.py` | `uacp dev oracle-bakeoff` | dev/read-only | research; CLI-only |
| `scripts/live_guardian_probe.py` | `uacp dev guardian-probe` | dev/read-only | diagnostic; CLI-only |

Subcommand groups: `uacp {tool, lint, fmt, verify, check, migrate, dev}`. MCP exposes
governed-mutating (today) + optionally the read/validate checks; **`migrate` (operator-mutating) and
`dev` (read-only) are CLI-only** (operator surface, never an agent tool) — and `migrate` MUST emit the
audit record for its mutations (node 00 §4).

## 2. The registry generalization (the one real change)

Extend the single registry from `ToolSpec` (governed tools only) to a `Command` record carrying:
`name` (dotted, e.g. `migrate.knowledge-corpus`), `class` (node 00 §3), `handler` (the callable —
the existing handlers + the scripts' `main()`s, lifted to importable functions), an **argparse spec**
(so the CLI builds `--flags` from the registry, not per-script), and the `inputSchema` (for MCP /
validation). The 11 `ToolSpec`s become `Command`s unchanged — **8 governed-mutating + 3 read-only**
(the existing `read_only` flag becomes `class`). The 12 scripts' entry functions become handlers:
refactor each entrypoint — `main()`, or a named one like `migrate_knowledge_corpus.py`'s `migrate(root)`
(which has no `main()`) — into an importable `run(args)` + a thin `if __name__` shim, so they keep
working standalone during migration.

## 3. Build plan (DEFERRED until after Phase C — ratchet, each step suite-green)

1. **Generalize the registry** — `Command` record + `class`; the 11 tools become Commands (no behaviour change; MCP adapter reads the same registry).
2. **Add the CLI adapter** — `cli.py` (`main()`) building an argparse tree from the registry; `pyproject [project.scripts] uacp = "uacp_cli:main"`. Dispatches `spec.handler(args)` (mirrors the MCP server). `--output-format text|json`.
3. **Fold `lint`/`fmt` first** — these are built in Phase C (node 33); register them → `uacp lint`/`uacp fmt`. Proves the read/validate class end-to-end.
4. **Migrate the rest incrementally** — one script → one Command per step (extract `run(args)`, register, point the CLI at it, keep the `__name__` shim until callers move). Order by the §1 class column: read/validate (verify, check) → **operator-mutating** (migrate — with audit) → dev/read-only (probe, bakeoff). **Decouple Hermes-coupled scripts FIRST:** `phase0_verify.py:23-38`, `import_loader_verify.py:29-34`, `live_guardian_probe.py:49-51` import `runtime-adapters/hermes/plugins/uacp_guardian` — they must depend on the kernel/`engines`, not the Hermes plugin, before folding into the runtime-neutral CLI (so this step is more than a `main()→run(args)` rename for them).
5. **Retire the bare `python3 scripts/X.py` invocations** — update CI + docs to `uacp <cmd>`; delete the shims once nothing calls them directly.

## 4. Invariants (from node 00)
- A command is defined ONCE (the registry); CLI + MCP are thin dispatchers — no duplicated logic.
- Governed-mutating commands run the same self-enforcing handlers (path containment) via CLI + MCP — but the CLI is an OPERATOR surface that does NOT get the agent-runtime's Layer-1 Guardian phase/mode gate, so it MUST still emit the audit record, and agents mutate only via the runtime-gated path (node 00 §4 — not "no bypass").
- Adapters import the registry inward; the registry imports no adapter.

## To expand
- The argparse-spec shape in the `Command` record (how a handler declares its flags).
- `uacp` top-level UX: `uacp --help` groups; exit codes (lint/verify non-zero on findings, for CI).
- Whether `tool_specs.py` is renamed/relocated to a `commands` module as it absorbs non-tool commands.
