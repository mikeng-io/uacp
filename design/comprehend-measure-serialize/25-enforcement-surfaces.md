---
type: analysis
title: Enforcement surfaces — architecture (governance/execution) + prompt-injection (cognition)
description: CMS is a coherence invariant imposed across THREE layers (governance, execution, LLM cognition) via TWO enforcement mechanisms. Architecture (Guardian/Heartgate/gates/entity-writer) enforces the governance + execution layers, where compliance is mostly natural. System-prompt injection (UACP.md) enforces the cognition layer, where it is not — the prompt is the only lever for an LLM's internal reasoning. This is why the portable preamble is enforcement, not decoration.
tags: [coherence, enforcement, cognition, prompt-injection, governance, architecture]
timestamp: 2026-06-24
edges:
  - {dst: 00-the-axiom, rel: extends, provenance: asserted}
  - {dst: 22-trustless-differentia, rel: depends_on, provenance: asserted}
---

# Enforcement surfaces — two mechanisms, three layers

CMS is one coherence invariant ([00](00-the-axiom.md)) imposed across three layers. Each layer is enforced by the mechanism appropriate to it. The coherence is the point: the same discipline, top to bottom, so the layers cannot drift apart.

| Layer | What it disciplines | Compliance | Enforcement mechanism |
|---|---|---|---|
| **Governance** | the lifecycle (writes, transitions, evidence) | mostly **natural** | **architecture** — Guardian (governed-writers-only) · Heartgate (phase-exit gates) · the entity-writer (validate-on-write + watermark + register) |
| **Execution** | the actual work (the mutations + their evidence) | made to comply | **architecture** — the same gates + checkpoint coverage in the graph projection |
| **Cognition** | the LLM's own reasoning | **not natural** — it skips comprehension, re-interprets downstream, asserts without evidence | **system-prompt injection** — the portable [`UACP.md`](../../UACP.md) prepended to the agent's instructions |

## Why two mechanisms (and why prompt-injection is real enforcement)

You **cannot infra-gate an LLM's internal reasoning.** There is no Guardian hook between "the model reads the context" and "the model concludes." The only lever on that surface is the **instruction the model is reading** — the system prompt. So injecting CMS into the prompt is not a slogan substituting for a mechanism; on the cognition surface it **is** the mechanism. There is no stronger one available.

This dissolves the "decoration" objection (the cross-provider panel's strongest standalone attack): the charge was *"nothing enforces `UACP.md`."* That conflates **not-infra-enforced** with **not-enforced**. The cognition layer is enforced by the prompt, by construction — because that is the only thing that can enforce it. The real gap the panel found is a **build gap** (the injection is not yet wired into the plugin), not a conceptual one. → the fix is to **build the injection**, not to soften the claim.

## The honest split: mechanized vs normative disciplines

Not every CMS discipline is mechanically checkable. State which is which, or you overclaim:

- **Mechanized** (architecture verifies these): `serialize` provenance + canonical shape (validate-on-write, watermark, register); coverage / orphan / contradiction (the graph projection); phase-exit invariants (gate-ledger + graph_invariant).
- **Normative** (the prompt instructs; no full mechanical check exists): `comprehend` *interpret-once* (the kernel cannot tell whether the model re-interpreted downstream); `measure` *bind-to-the-real-property* (whether evidence is a real measurement vs a weak proxy is a judgment — the #503 lesson is not fully automatable). These live on the cognition surface precisely because they resist mechanization — which is *why* the prompt-injection surface exists.

## Consequence

The portable `UACP.md` is the **cognition-layer enforcement payload**, peer to the architecture — not a lesser, decorative restatement of it. The two surfaces together are what make the invariant *coherent*: an agent governed only by gates would still reason incoherently inside each step; an agent prompted only by `UACP.md` would reason coherently but commit ungoverned state. Both, and only both, give one discipline end-to-end.

## To expand
- The injection mechanism itself (plugin install → prepend `UACP.md` to the host CLAUDE.md/AGENTS.md) — the build task.
- Tiering: cognition-only (prompt) vs cognition+governance (prompt + MCP/Guardian) installs.
- Whether any normative discipline can be *partially* mechanized (e.g. an independence pre-screen for bind-to-real-property).
