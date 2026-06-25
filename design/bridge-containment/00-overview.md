---
type: analysis
title: Bridge Containment — Why & the Boundary-We-Own Principle
description: Why an external reviewer needs containment (it runs outside the Guardian), the organizing principle (enforce/capture at a boundary UACP owns, fail-closed), and what is in/out of scope.
tags: [bridge, containment, read-only, guardian, boundary, review]
timestamp: 2026-06-25
edges:
  - {dst: 10-containment-ladder, rel: relates_to, provenance: asserted}
---

# Bridge Containment — Intent

## The problem

UACP dispatches reviews to **external coding agents** via bridges (`skills/uacp-bridge/references/*.md`): codex, gemini, opencode, kimi, claude, reasonix, hermes. For a review (`capability_profile: inspect`) the reviewer must be **read-only** — it must not mutate the code it reviews — and must use only an **authorized model/provider**.

Two facts make this non-trivial:

1. **The Guardian does not see a shelled-out reviewer.** UACP's kernel enforcement (Guardian PreToolUse hook + governed writers) intercepts the *host runtime's* tool calls. When a bridge runs `codex exec` / `reasonix run` / `gemini -p` as a child process, that process does its own filesystem and network I/O directly — the Guardian never observes it. So read-only is **not** kernel-guaranteed for bridges.
2. **Bridges are reference docs an LLM follows, not executable code.** "Fail-closed" rules written in a bridge `.md` bind only insofar as the orchestrating LLM honors them — unless a rule is backed by a callable check or an OS/runtime control.

## The principle

> **Enforce and capture at a boundary UACP owns — not inside the agent — and fail closed.**

The agent (its read-only mode, its self-reported model, its self-reported coverage) is the *least* trustworthy place to enforce or measure. The trustworthy boundaries are the ones UACP controls regardless of which agent it is: the **filesystem** it provisions (worktree / read-only mount), the **OS sandbox / container** it runs the agent in, and the **MCP tool layer** it serves the agent's tools from. This mirrors UACP's CMS discipline — *determinism belongs to the verifying gate, not to the agent's judgment* (`[[uacp-core-principle-comprehend-measure-serialize]]`).

This also resolves the **host-can-also-be-a-bridge** case (hermes is both UACP's host runtime *and* a dispatch target): containment applies to the dispatch target regardless of whether that runtime is also a host.

## Honesty constraint

Because most controls here are convention (LLM-followed) rather than code/OS-enforced, the design's hardest rule is: **never describe a convention-tier control as a hard guarantee.** A cross-provider council (2026-06-25) caught exactly this overclaim (a git worktree described as protecting "regardless of tool behavior"). The ladder ([[10-containment-ladder]]) is explicit about which tiers are code/OS-enforced and which are convention.

## Scope

- **In:** read-only containment + model authorization for external reviewer bridges; capturing review evidence at fidelity.
- **Out:** sandboxing implementation/`modify` tasks (those follow worktree-protocol for their own branch); Guardian/kernel changes; building a chat-broker product.
