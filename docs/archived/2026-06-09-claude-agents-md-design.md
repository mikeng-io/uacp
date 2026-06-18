---
type: design
title: "Design: CLAUDE.md and AGENTS.md for UACP Root"
description: "Design for adding runtime instruction files at the UACP root to orient Claude Code and Codex agents"
tags: ["claude-code", "agents", "governance", "runtime"]
timestamp: 2026-06-09
status: archived
---

# Design: CLAUDE.md and AGENTS.md for UACP Root

**Date:** 2026-06-09  
**Status:** approved  
**Scope:** Add two runtime instruction files at the UACP repo root

---

## Problem

AI coding tools (Claude Code, Codex) working in this repo have no project-level
instruction file at the root. They cold-start without governance orientation, risking
the most common failure modes: writing directly to main, skipping TRIAGE, using raw
filesystem writes instead of governed writers, or asserting evidence rather than
producing it.

The `docs/` tree is authoritative but too deep to orient a cold runtime quickly.

---

## Decision

Create two files at the repo root:

| File | Role | Size |
|---|---|---|
| `AGENTS.md` | Canonical runtime instruction file (all governance rules) | ~70 lines |
| `CLAUDE.md` | Thin Claude Code adapter — `@AGENTS.md` + Claude-specific dispatch | ~15 lines |

**Rationale for AGENTS.md as canonical source:**
Codex is the primary review engine in UACP's council gate (see `CONTRIBUTING.md#council-review-gate`).
AGENTS.md is its native instruction convention. Making it canonical means a single file
holds all governance rules — CLAUDE.md never drifts because it imports rather than duplicates.

**Why `@AGENTS.md` import in CLAUDE.md:**
Claude Code's `@file` syntax pulls the referenced file's content at load time. Zero
maintenance: update AGENTS.md once, CLAUDE.md stays current automatically.

---

## AGENTS.md Structure

### 1. Identity (2 lines)
One-sentence repo description + lifecycle tagline. Sourced from README.md.

### 2. Authority Chain (6 lines)
Priority order: `docs/` > `config/` > `state/` > `skills/`. Pointer to `docs/INDEX.md`
as the canonical agent read order. Note that skills and config do not override docs.

### 3. Lifecycle Summary (10 lines)
Phase table (TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE) with one-liner
per phase. Note that every transition is Heartgate-gated. Direct phase-skipping is a
blocker, not a warning.

### 4. Key Invariants (10 lines)
Five non-negotiable rules — all mechanically enforced or authoring-contract level:

1. All non-trivial work enters via TRIAGE — no phase-skipping
2. No writes to `main` during an active run — use `worktree` or `branch`
3. No raw filesystem writes — governed writers only
   (`uacp_doc_write`, `uacp_state_write`, `uacp_config_write`,
   `uacp_gate_ledger_append`, `uacp_run_registry_update`, `uacp_escalation_event`)
4. Council review required before any kernel / policy YAML / canonical doc change
   exits PLAN (zero material findings unresolved)
5. Evidence must be produced (artifact + ledger entry), never asserted ("done" with
   no backing artifact is a Heartgate blocker)

### 5. Skill Map (8 lines)
Table: phase → skill to invoke. Columns: Phase | Skill | Purpose.

### 6. Cognitive Planes (5 lines)
One-paragraph summary of the 5-plane model (UACP / Agent Council / Coordination
Adapter / Agent Runtimes / Tool Adapters + Guardian+Heartgate). Prevents the most
common category error: using Agent Council as a state database or letting worker
runtimes silently mutate UACP phase state.

### 7. Codex-Specific Dispatch (15 lines)
- Native dispatch (preferred when executor is Codex + multi-agent enabled)
- MCP server path: `mcp__codex__codex` / `mcp__codex__codex-reply`
- CLI fallback: `codex exec` flags (`--sandbox read-only`, `--ask-for-approval never`,
  `--json`, `--ephemeral`)
- Reference to `skills/bridge-codex/SKILL.md` for full dispatch contract

---

## CLAUDE.md Structure

```
@AGENTS.md

## Claude Code — Runtime-Specific

[~15 lines covering:]
- Native Task tool dispatch (preferred — sub-agents per domain)
- Agent Teams path (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1, with TeamCreate guard)
- Workflows path (tier ≥3, research/audit modes, or ultracode keyword)
- Worktree isolation: use Agent tool with isolation: "worktree" for parallel file mutations
- Reference to skills/bridge-claude/SKILL.md for full dispatch contract
- --dangerously-skip-permissions note for non-interactive -p mode
```

---

## What This Does NOT Include

- Full CONTRIBUTING.md content (pointer only — link to CONTRIBUTING.md)
- Governed writer implementation details (pointer to docs/runtime/runtime-enforcement.md)
- Proposal schema (pointer to docs/reference/proposal-schema.md)
- Phase 5 roadmap (pointer to ROADMAP.md)

These live in docs/ and are authoritative there. Duplication creates drift.

---

## Files Changed

| Path | Action |
|---|---|
| `AGENTS.md` | Create (new file at repo root) |
| `CLAUDE.md` | Create (new file at repo root) |

No other files are modified. This is additive only.
