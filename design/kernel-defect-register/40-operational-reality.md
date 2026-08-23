---
type: analysis
title: Operational reality — inertness, portability, and what a governed run costs
description: D-14 to D-18. The enforcement surface is off in this repo, Claude-only elsewhere, and a full_governance run is the most expensive thing UACP does.
tags: [operations, cost, portability, plugin]
timestamp: 2026-08-22
edges:
  - {dst: 00-register, rel: depends_on, provenance: derived}
  - {dst: 30-emission-defects, rel: extends, provenance: asserted}
---

# Operational reality

Everything in `10`–`30` describes the machine as designed. This node is about whether it is
running at all.

## D-14 — The plugin is not enabled in this repo · VERIFIED

- `~/.claude/settings.json` → 54 `enabledPlugins` entries, **zero** containing `uacp`
- `.claude/settings.local.json` → `"enabledPlugins": {}`, `"hooks": {}`
- `~/.claude/plugins/installed_plugins.json` → 0 occurrences of `uacp`

So in the UACP repo itself, right now: the SessionStart injection does not fire, the Guardian
PreToolUse hook does not fire, and none of the 18 governed writers are exposed. The only UACP
content reaching an agent here is `CLAUDE.md` → `AGENTS.md`.

This is not a code defect; it is the state that makes every other defect hard to notice. UACP is
developed in an environment where UACP is off. That is the mechanism by which "the tooling
survives, the mandate does not" keeps happening — the mandate is never felt during development.

It also invalidates a class of reasoning: any claim of the form *"the hook would have caught
that"* is untested here, and any dogfooding claim needs the plugin enabled first.

## D-15 — The cognition surface is Claude-only · REPORTED

`runtime-adapters/claude/hooks.json` registers the SessionStart injector and the Guardian
PreToolUse hook. Reported for the others: `kimi.plugin.json` ships `skills` + `mcpServers` with
no `hooks` key; the Codex adapter directory is a README with no adapter code; Hermes registers
`pre_tool_call` / `post_tool_call` only; there is no opencode adapter.

`UACP.md`'s own header concedes it: *"Other runtimes … need their own session-start hook … until
then their cognition surface is unenforced."*

Two consequences worth separating. First, cross-runtime council and bridge work runs against
agents that never received the preamble. Second, the injector declares **no `matcher`**, so
where it does fire it fires on every source including `compact` — which makes UACP's
compaction posture mechanical rather than doctrinal, on Claude, and absent everywhere else.

## D-16 — A `full_governance` run costs ~405 agent invocations · ESTIMATE

Assumptions, stated because the number is derived rather than measured: 4 chars ≈ 1 token; read
costs are `wc -c` of files the skills mandate; Tier-1 returns ~2 KB/agent; Tier-2 bridge reports
~15 KB.

| Scope | Invocations | Coordinator context |
|---|---|---|
| One Tier-1 council (3 domains, standard) | 10 | ~54k tokens |
| One Tier-3 council (5 bridges, 5 domains) | 81 | ~126k tokens |
| Standard-track run (3 × Tier-1) | ~30 | ~162k tokens |
| `full_governance` run (5 × Tier-3) | **~405** | **~630k tokens** |

The fixed read cost before any agent runs is ~40k tokens — `council-taxonomy` 18.5k chars,
`uacp-bridge/SKILL.md` 46k chars, the domain registry 50k chars. For Tier 2 the adapter
references are read *and re-emitted verbatim* into each bridge prompt, so they are paid twice.

Exactly one dispatch path hands work over as **file paths** rather than pasted text: the debate
coordinator at `standard`/`thorough` intensity, which passes `round-{k}/` pointers. Everything
in `uacp-council` and `uacp-bridge` interpolates payloads as strings, and stateless bridges are
instructed to *embed* prior rounds up to a 32,000-character cap.

This is the number to check before importing any per-unit review loop from elsewhere: UACP's
review path is already the most expensive thing it does.

## D-17 — Independence is orchestrator convention, not enforcement · REPORTED

Built, with tests: `skills/uacp-council/scripts/review_sandbox.sh` (detached ephemeral worktree,
fail-closed on non-zero exit) and `skills/uacp-council/scripts/check_model_authorized.py`
(exit 3 on an unauthorized model, with `enforce_model_allowlist = true`). Also built: a council
synthesis must carry `dispatch_surfaces` and a **non-empty `inspected_paths`**
(`scripts/validate_uacp_artifacts.py:388-398`) — the only grounding check on a review — and
`followup_depth > 1` blocks.

Reported gap: **nothing in the kernel invokes either script.** Their only callers are tests;
they run if and only if the orchestrating agent chooses to follow the dispatch reference.
`read_only_enforcement` and `model_authorized` arrive as self-declared report fields with no
validator behind them.

This is the same shape as D-05 and D-06 — capable tooling, agent-elected — applied to the one
property (reviewer independence) that `design/council-reviewer-independence/` already
identified as faked by runtime-swap alone.

## D-18 — The router is majority incident log · REPORTED

`skills/uacp/SKILL.md` is 145 lines with a frontmatter description promising a router. Reported
word split of the body: **15% routing logic · 28% durable doctrine · 57% accreted
session-specific correction** — sections keyed to past incidents, naming the operator directly
seven times in second-person conditionals, and hard-coding out-of-project entities.

Two costs. It is read at routing time and routes almost nothing; and the knowledge inside it is
real, hard-won, and in the wrong shape — narrative rather than a decision-point rule, in the
router rather than in the skill that owns the decision.
