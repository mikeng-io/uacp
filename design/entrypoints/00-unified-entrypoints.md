---
type: contract
title: Unified Entry Points — one command registry, CLI + MCP as thin adapters
description: >-
  The kernel's ENGINES follow CA+DDD, but the ENTRY RING is fragmented — 12 standalone
  scripts/*.py with no common registry or governance, alongside the 11 governed tools which DO
  have a registry (tool_specs.py) + an MCP adapter. This node sets the target: ONE command
  registry (the application layer) with two THIN adapters over it — a single `uacp` CLI and the
  existing MCP server. Grounded: tool_specs + the MCP server ALREADY are this pattern for the 11
  tools; the CLI is the symmetric second adapter; the work is generalizing the registry to hold
  the scripts' capabilities too. Build deferred until after Phase C (the Manifest engine).
tags: [uacp, entry-points, cli, mcp, command-registry, clean-architecture, tool-surface]
timestamp: 2026-06-23
edges:
  - {dst: 01-command-map, rel: depends_on, provenance: asserted}
---

# Unified Entry Points — one registry, two thin adapters

> **Why this exists.** The engines are CA+DDD-clean (`engines/domain` sink, gates/checks in the
> application ring, adapters at the edge), but the **entry ring is not**: `scripts/` holds **12
> standalone `.py` files** (`validate_uacp_artifacts` 95 K, `phase0–4_verify`, migrations, probes,
> bakeoff) each invoked as a bare `python3 scripts/X.py` — no common registry, no shared governance,
> no single command-line of control. Meanwhile the **11 governed tools** already have a clean
> registry + one adapter. This node unifies the entry ring to match the engines' discipline.

## 1. The pattern (CA applied to the entry ring)

**One command registry (the application layer) + thin adapters (the framework ring).** A *command*
is defined once — name, input schema, handler, and class — in a registry; the **CLI** and the **MCP
server** are each a thin dispatcher over it. Neither adapter holds command logic; both resolve a
name → the one handler. (Dependency rule: adapters depend inward on the registry; the registry never
imports an adapter.)

## 2. This is EXTEND, not greenfield (grounded in as-built)

The pattern already exists for the 11 governed tools — only one adapter is missing:

- **Registry:** `skills/uacp-core/scripts/tool_specs.py` — `tool_specs() -> list[ToolSpec]`, each
  `ToolSpec{name, description, schema, handler: (args:dict)->str}`. Single source of truth, true DRY.
- **MCP adapter (exists):** `runtime-adapters/mcp/uacp_mcp_server.py` — *"a thin, faithful exposure of
  `tool_specs()` over MCP — nothing more"*: `list_tools()` enumerates the specs; `call_tool(name,
  args) → spec.handler(args)`.
- **CLI adapter (the gap):** a `uacp <command> [args]` console entry that does the **symmetric** thing
  — resolve the spec, call `spec.handler(args)` — via `pyproject [project.scripts] uacp = "...:main"`
  over stdlib `argparse` (no new dep; several scripts already use argparse).

So the CLI is ~1 thin module mirroring the MCP server. The real work (node 01) is **generalizing the
registry** from "the 11 governed write tools" to "all commands," so the 12 scripts' capabilities live
in it too and both adapters expose them.

## 3. Generalize the registry: command CLASS

The registry grows a **class** per command, telling each adapter what to expose and how to gate.
**The seed already exists:** `tool_specs.py` marks 3 of its 11 tools `read_only=True`
(`uacp_sandbox_check`, `uacp_heartgate_check`, `uacp_oracle_query`) — so the registry already
distinguishes mutating from read; `class` generalizes that flag.

| Class | Examples (today) | Gating | CLI | MCP |
|---|---|---|---|---|
| **governed-mutating** | the **8** `uacp_*_write` / state writers (of the 11 tools) | Layer-1 Guardian gate (agent runtime) + handler self-enforcement (§4) | yes (`uacp <tool>`, operator) | yes (today, agent) |
| **read / validate** | the **3 read-only** governed tools (`sandbox_check`/`heartgate_check`/`oracle_query`, already `read_only=True`); `validate_uacp_artifacts` → `uacp lint`; `uacp fmt`; the phase verifiers; the link/import checks | none / read-only | yes | optional (agent-facing checks) |
| **operator-mutating** | the migrations (`migrate_*` — `shutil.move` files, `rename` dirs, rewrite `.gitignore`/config) | **audit required** (no agent phase-gate — operator context — but mutations MUST be logged, §4) | yes (`uacp migrate …`, operator) | **no** |
| **dev / read-only** | probes, bakeoff (diagnostic/research, no governed mutation) | none | yes (`uacp dev …`) | **no** (operator-only) |

## 4. Enforcement: the CLI is a DIFFERENT trust context (security — Kimi-corrected)

Two enforcement layers exist, and they live in different places (verified):
- **Layer 1 — the Guardian gate + audit**: `Guardian.evaluate` (phase-allowlists/forbidden
  `guardian.py:319-375`, mode blocks `:190-214`) + audit emission (`hook_kernel.py:181-191`). This
  lives in the **PreToolUse hook**, applied by the **agent runtime** — NOT in the MCP server (which
  adds no Guardian wrapping) and NOT in the handlers.
- **Layer 2 — handler self-enforcement**: path containment only (`_validate_common_write_args` +
  `_resolve_uacp_path` + the allowed-roots check). The handlers `GuardianPolicy.load()` but never
  `.evaluate()` — so they enforce *where*, not *phase/mode*, and emit no audit.

**Correction to an earlier claim:** a standalone `uacp` CLI dispatching `spec.handler` gets **only
Layer 2**. It skips the phase/mode gate AND the audit record. So the CLI is **not** "the same
enforcement as MCP" — it is **weaker** unless we add Layer 1. (MCP only gets Layer 1 because an
agent *runtime* wraps it with the PreToolUse hook; nothing wraps a bare CLI.)

**Design decision (must hold, not gloss):**
1. The CLI is an **operator-trusted** surface (a human outside a governed run); the phase/mode gate is
   contextually N/A there (no agent, no phase). That is acceptable — but must be *explicit*, not framed
   as "no bypass."
2. For **governed-mutating** commands the CLI adapter MUST still **emit the audit record** (call the
   same `write_audit_record` path) — operator mutations stay logged; losing audit is not acceptable.
3. **Agents never reach mutations via the raw CLI** — an agent mutates only through the runtime-gated
   path (MCP/tool-call under the PreToolUse hook). The CLI's governed-mutating commands are an operator
   affordance; if an agent is ever given the CLI, it must be behind the same Layer-1 hook.
4. **Read-only** commands (read/validate + dev/read-only) have nothing to gate — Layer-1 N/A by
   construction. But **operator-mutating** commands (the migrations — they `shutil.move`/`rename`/rewrite
   `.gitignore`+config) ARE mutators: no agent phase-gate (operator context), but they MUST emit the
   audit record, same as governed-mutating (point 2). **Mutation, not "dev-ness", decides the gate.**

## 5. Relationship to existing decisions

- **D8 / node 33** (`uacp-lint` + `uacp-fmt` = one skill, two subcommands over `schema.py`) are the
  FIRST commands folded into this registry — `uacp lint` / `uacp fmt`. This bundle is the umbrella
  that the lint/fmt CLI plugs into, not a competing CLI.
  See [graph-engine/02-decisions](../graph-engine/02-decisions.md) — D8 (uacp-lint/fmt) and node 33
  (schema-reconciliation) are the load-bearing decisions from that bundle that ground this entry-point
  design.
- **node 34** (Manifest engine) + the governed writers are the governed-mutating class's home; the
  CLI/MCP adapters expose them, the engine owns them.

## 6. Build sequencing — DEFERRED until after Phase C (mike, 2026-06-23)

Design recorded now; build after the Manifest engine lands, because `uacp-lint`/`uacp-fmt` (node 33)
are built as part of Phase C and are the first registry commands. Then (node 01 has the full plan):
generalize the registry (+ class) → add the CLI adapter over it → migrate the 12 scripts into
registry-backed commands incrementally (ratchet, `lint` first) → wire `pyproject [project.scripts]` →
the MCP adapter stays in sync for free (same registry).

## To expand
- The exact `Command`/registry record (extend `ToolSpec` with `class` + an argparse spec) — node 01.
- Whether the registry stays in `tool_specs.py` or relocates to a `commands/` module as it grows.
- Output conventions (the handlers return JSON strings today — fine for MCP; the CLI needs a
  text/JSON `--output-format`, mirroring how `kimi -p` offers `text|stream-json`).
