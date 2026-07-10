---
type: analysis
title: Leading narrative vs the engagement specification — the two things the dispatch payload conflates
description: The load-bearing distinction. task_description/context_summary carry BOTH the orchestrator's opinion (leading) AND the pointer to what is under review including the diff (specification). Independence requires stripping the first while preserving the second; emptying both starves the reviewer. Documents the two concrete starvation modes (MCP no-cwd, uncommitted-diff-in-prompt).
tags: [narrative, engagement-spec, minimal-non-leading, starvation, mcp, diff]
timestamp: 2026-07-10
edges:
  - {dst: 00-problem, rel: motivated_by, provenance: asserted}
---

# Leading narrative vs the engagement specification

## The distinction

A real outside auditor exercises independent **judgment** but is still handed **the books and an
engagement letter** — they are told *which entity and period* they are auditing; they are not told
*what conclusion to reach*. Two different things live inside the council's dispatch payload today,
and the naive patch fails because it cannot tell them apart:

| | **Leading narrative** | **Engagement specification** |
|---|---|---|
| What it is | The orchestrator's opinion: expected findings, suspected root cause, preferred design, desired verdict, "here is what this change does and why it's correct" | The neutral pointer to the object under review: which artifact, which scope, and — critically — **the diff / baseline pointer** so the reviewer knows *what changed* |
| Effect on independence | Anchors the reviewer to the author's conclusion → self-attestation by proxy | None — it is the minimum a reviewer needs to review *the right thing at all* |
| Correct treatment for an external reviewer | **Strip it** | **Preserve it** |

`task_description` and `context_summary` currently carry **both**. That is why "just empty them"
is wrong: it removes the narrative (good) and the specification (fatal).

## The two starvation modes (why emptying is not merely insufficient but harmful)

These are the concrete mechanisms the subagent audit surfaced; they are the reason the
specification half must be preserved, not blanked.

### Mode 1 — MCP has no working directory

`mcp__codex__codex` accepts only `prompt`, `approval-policy`, `sandbox`, `model`, `reasoning`,
`base-instructions`. There is **no `cwd` / `--cd` / `--dir`**. The Phase 4.0 containment design
points a *CLI* bridge at the ephemeral worktree via cwd — but the MCP path (the *preferred* path
for non-Codex runtimes, per `codex.md` connection_preference) cannot be pointed at `$SANDBOX` at
all. On that path, the **only** channel that can tell the reviewer *what artifact to review* is the
prompt text — i.e. exactly `task_description` / `context_summary`. Empty them and the MCP reviewer
has neither narrative nor pointer, and is (separately) still aimed at wherever the server launched.

> This also exposes a pre-existing containment gap on the MCP path (it never actually reaches
> `$SANDBOX`). That is out of scope here — flagged for [[20-blast-radius]] / bridge-containment —
> but it means the engagement spec on the MCP path is *load-bearing for correctness*, not a nicety.

### Mode 2 — the worktree does not encode what changed

The review sandbox is a `--detach` worktree at a single ref (`review_sandbox.sh`). It shares
`.git`, so `git log` / `git show` work — but it is a **snapshot**, with nothing marking
baseline-vs-change. For the common **uncommitted-diff** review, `phase-4-dispatch.md:18-19` is
explicit: *"embed the diff in the prompt (the sandbox is at the committed ref)."* The change under
audit therefore exists **only** in the prompt. Emptying `context_summary` deletes the sole copy of
the change; the reviewer audits pre-change code, unaware anything changed. Even for a committed
change, the worktree gives the post-change state but no baseline pointer — the reviewer cannot know
*which commit is under review* unless the specification tells it.

## The resolution: `minimal-non-leading`, already in the repo

The repo already names the correct axis. `uacp-bridge/SKILL.md` defines a `context_policy` with a
`minimal-non-leading` value, and `uacp-council` brainstorm-mode discipline already specifies exactly
the right split for Round 1: **exclude** expected findings, suspected root cause, coordinator's
preferred architecture, other participants' findings, desired verdict — while still providing scope,
goal, and hard constraints.

The defect is that this discipline is **not plumbed into `runtime_input`** and is **scoped only to
brainstorm/discovery**, so for `review` / `audit` — the actual Deloitte case — non-leading framing
is unenforced. The correct fix is therefore *not a new concept*: it is applying the existing
`minimal-non-leading` policy to the external-reviewer dispatch, with an explicit **retain-vs-strip**
contract that keeps the engagement specification (scope + diff/baseline pointer) intact. That
contract is [[10-minimal-non-leading-dispatch]]; making the reviewer's *pull* measurable rather than
hoped-for is [[11-grounding-provenance]].
