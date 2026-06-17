---
type: analysis
title: Trustless ACP → UACP Source Analysis
description: "\"What's Universal\" 14-pattern table, 6 architectural derivation decisions for UACP, bridge-name reference table (claude/codex/opencode/gemini/kimi). Historical reference only."
tags: [trustless-acp, history, architecture, analysis]
timestamp: 2026-06-17
---

# Trustless ACP → UACP: Source Analysis

Historical reference only. This file explains what was extracted from Trustless ACP and what was left behind; it is not current UACP authority.

## What's Universal (Extracted to UACP)

| Pattern | How It Manifests |
|---------|-----------------|
| Phase-gate enforcement | Preflight before transition — if check fails, phase blocked |
| Explicit state ownership | State owned by dedicated skill, not agents |
| Constitutional rule hierarchy | Axioms → invariants → specs → execution |
| Spec supremacy | Code bows to approved specification |
| Conservative failure | Missing → hard BLOCK, no silent fallback |
| Actor-indifferent rules | Same rules apply to all agents |
| Write containment | Implementation writes contained to designated workspace |
| Mandatory escalation stops | Defined stop conditions require human clarification |
| Immutable audit trail | Gate results in JSONL ledger with timestamps |
| Multi-agent adversarial council | DA 40% + experts, 5-phase debate |
| Retrieval-led reasoning | Oracle query 8 layers, decision tree before reasoning |
| Gate-based verification pipeline | Sequential gates, each must pass before next |
| Expert tier architecture | core/domain/dynamic |
| Provider-neutral external reviewer dispatch | YAML config + fallback chain |

## 6 Architectural Derivation Decisions for UACP

1. **Guardian = skill hooks, not standalone CLI** — preflight checks integrated into lifecycle skills
2. **State = uacp-state skill** — runtime-native, not a Python CLI
3. **Review = agent-council + deep-council** — adaptive based on context/scope/intensity
4. **Constitution = universal axioms** — not financial platform specific
5. **Workspace = runtime workspace routing** — worktree/scratch/dir: (not `.trustless/worktrees/`)
6. **Kanban integration** — lifecycle phases map to Kanban tasks with dependency gates

## Bridge-Name Reference Table

Known UACP bridge adapter references:

| Runtime | Bridge reference |
|---------|-----------------|
| claude | `uacp-bridge/references/claude.md` |
| codex | `uacp-bridge/references/codex.md` |
| opencode | `uacp-bridge/references/opencode.md` |
| gemini | `uacp-bridge/references/gemini.md` |
| kimi | `uacp-bridge/references/kimi.md` |
