---
type: design
title: "`.uacp/` Namespace + Config Collapse (Design)"
description: "Design for consolidating UACP's per-project footprint under `.uacp/` and collapsing 13 config YAMLs into one `uacp.toml`"
tags: ["namespace", "config-collapse", "uacp-toml", "architecture"]
timestamp: 2026-06-15
status: archived
---

# `.uacp/` Namespace + Config Collapse (Design)

> **For Claude:** after approval, drive via `superpowers:writing-plans` → `superpowers:subagent-driven-development`.

**Date:** 2026-06-15
**Status:** approved (operator co-designed; all decisions confirmed)

---

## Goal

Consolidate UACP's entire per-project footprint under a single `.uacp/` namespace, and
collapse the 13 scattered config YAMLs into one `uacp.toml` (knobs) plus grammar-as-code —
so a new user gets one tidy dir, one config file, and a versioned framework they never
hand-edit. Subsumes the long-deferred Phase 2 config collapse from
`2026-06-14-uacp-cc-hardening.md`.

## Motivation

- **Scatter:** today UACP litters the repo root with `config/` (13 YAMLs), `state/`,
  `.outputs/`, `proposals/`, `plans/`, `executions/`, `verification/`, `knowledge/`.
- **The `config.toml` collapse was decided but never built** — only Phase 1 (E2E harness)
  and the computed-Heartgate engines shipped. The 13 YAMLs remain.
- **`.outputs/` is an inconsistent special-case** (every other phase writes to a
  phase-named dir; RESOLVE alone dumped to a generic `.outputs/`) — which is exactly how
  the `..outputs` typo (F-EV-01) could hide. Killing it removes the whole bug class.
- **Install model** (decided: kernel bundled in a Claude Code plugin) wants a clean
  framework/runtime split: framework ships in the plugin; the user's repo holds only
  `.uacp/`.

## Source of truth (not invented)

- **`config/roots.yaml`** already defines the layout: `UACP_ROOT.contains: [docs, config,
  proposals, plans, executions, verification, .outputs, knowledge, state]`. The redesign
  = redefining this roots map. roots.yaml frames physical paths as *environment bindings*
  → they are **knobs**.
- **`RunManifest`** is lean: `run_id, status, current_phase, authority, workspace,
  state_history, finalized_at` + `artifacts: dict[str,str]` (free-form `type→path`). Dirs
  come from roots, not the manifest.

## Architecture (decided)

**Framework (ships in the plugin/kernel; user never edits):** `uacp-*` skills, the Python
kernel (Guardian, Heartgate, engines, state machine), **grammar-as-code**, the **default
`uacp.toml`**, and default `knowledge/` templates.

**Per-project runtime (the ONLY UACP footprint in a user's repo):**
```
.uacp/
  config.toml      ← knob overrides ("custom config")
  state/           ← runs, gate-ledger, run-registry, current.yaml, escalations
  proposals/       ← TRIAGE + PROPOSE
  plans/           ← PLAN (scope, plan-selection)
  executions/      ← EXECUTE (checkpoints)
  verification/    ← VERIFY (piv-assessment, verify-selection)
  resolutions/     ← RESOLVE (closure, resolve-selection)   [replaces .outputs/]
  knowledge/       ← project-learned knowledge (overrides framework defaults)
```

**Three-way config split:**

| Tier | Lives in | Contents |
|---|---|---|
| **Knobs** | `uacp.toml` (default shipped + `.uacp/config.toml` override) | `[paths]` (the roots map: `.uacp/` base + per-phase subdir names), `[memory]` (Honcho, later), guardian mode + tool classification, model-registry, runtime-bindings, autonomy, slimmed review-routing + gate-selection, version-control |
| **Grammar** | Python code in the kernel (extends `engines/domain`) | phase graph + gates + phase-exit invariants (`phase-transitions`), `artifact-schemas`, run-state schema (`state`), `evidence-clusters` |
| **Resolver** | `config.py` | loads default `uacp.toml`, deep-merges `.uacp/config.toml`, resolves `[paths]`; Pydantic-typed accessor used by Guardian, Heartgate, engines, state machine |

**F-T3-01:** as grammar moves to code, normalize all adaptive gates to **fail-closed**
(absent config ⇒ enforce) and add a regression test.

## Migration (hard cut — no fallback)

`scripts/migrate_to_uacp_dir.py`, run once per repo:
- move `state/` → `.uacp/state/`, `.outputs/` → `.uacp/resolutions/`, and
  `proposals|plans|executions|verification/` → `.uacp/<same>/`, `knowledge/` →
  `.uacp/knowledge/`.
- emit a starter `.uacp/config.toml` (empty/minimal — defaults come from the shipped
  default).
- update **every** path reference in code, config-being-collapsed, and skills (the
  resolve phase's invariants/skills currently point at `.outputs/`; all collapse to
  `.uacp/resolutions/...`).
- no dual-read fallback — one source of truth immediately.

## Method (incremental, harness-guarded)

The 321 tests + E2E harness are the safety net. Green after each slice:
1. **`config.py` + default `uacp.toml` + `[paths]`** (roots → `[paths]`) + `.uacp/` path
   resolution (default+override merge). Repoint the path resolver; nothing else yet.
2. **Repoint runtime dirs** `state/` + `.outputs/`→`resolutions/` + the phase dirs under
   `.uacp/` via the migrate script; update references.
3. **Collapse knob YAMLs** (guardian mode/classification, autonomy, model-registry,
   runtime-bindings, review-routing, gate-selection, version-control, memory-policy) into
   `uacp.toml`; repoint readers to `config.py`.
4. **Move grammar YAMLs to code** (`artifact-schemas`, `state`-schema, `evidence-clusters`,
   then `phase-transitions` LAST — 859 lines, one stage at a time); repoint Guardian /
   Heartgate / engines; apply F-T3-01 fail-closed.
5. **Finalize**: delete old `config/*.yaml`, finish the migrate script, update
   `AGENTS.md`/`CLAUDE.md`/`docs/INDEX.md` path references.

## Testing

- The existing harness/engine/unit suites must stay green throughout (behavioral guard).
- New: `config.py` default+override merge tests; `[paths]` resolution tests (incl. an
  override relocating the base); a migrate-script test (old layout → `.uacp/` → suite
  green); the F-T3-01 fail-closed regression test.

## Out of scope (sequenced after — keeps this bounded)

- The Claude Code **plugin packaging** (bundle kernel + skills + hooks + MCP + default
  `uacp.toml`).
- The **Honcho memory adapter** (its `[memory]` knob slot is reserved in `uacp.toml`).
- **Prompt caching** (port from trustless).

## Success criteria

- One `.uacp/` per-project dir; no `config/`, `state/`, `.outputs/`, or phase dirs at the
  repo root.
- One `uacp.toml` (default + `.uacp/` override) via `config.py`; grammar is versioned
  code; `roots.yaml` and the other 12 YAMLs are gone.
- `.outputs`/`..outputs` token eliminated everywhere (F-EV-01 class closed).
- Adaptive gates fail-closed. Full suite green; migrate script proven.
