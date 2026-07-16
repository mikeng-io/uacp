---
type: analysis
title: The Proving Ground — one apparatus, two readouts (root)
description: A contained REAL-agent substrate that runs an agent through UACP's actual plugin/MCP/hook surface and observes the result from outside the jail. One apparatus, two readouts — a conformance TEST verdict (does the lifecycle engine run normally under a real agent) and BENCHMARK scores (does governance help — bare vs +UACP, weak vs strong harness). The honest successor to self-diagnosis, whose driver was scripted/in-process with no agent consuming the product. Deliberately thin.
tags: [proving-ground, test-bench, benchmark, dogfood, root]
timestamp: 2026-07-17
edges: []
---

# The Proving Ground (root)

> **DRAFT — for red-pen.** Serialized 2026-07-17 from the benchmark/neutral-substrate thread
> (mike + Claude) so the design survives the session. This node stays thin; substance in 10–50.

## What it is
A **universal substrate** that runs a **real agent** (Claude Code, Hermes; later Pi/opencode/…)
**inside a container**, with or without the UACP runtime (plugin / MCP / hooks) **inside that
container with it**, against a **local model** (Metal-accelerated host ollama) or a cloud API —
driven over **one transport** (ACP), and observed **from outside the jail** by a deterministic
observer that reads only the emitted trail.

## One apparatus, two readouts
The same run yields both:

1. **Test verdict** — *does UACP run normally when a real agent consumes it?* The observer's
   L1–L4 engine-conformance gates (30): transitions through the apparatus, gates non-vacuous,
   terminal reached, plumbing persisted. This is the **real agent-through-tools dogfood** that
   has been outstanding since the scripted attempts.
2. **Benchmark scores** — *does governance help, and at what cost?* The cell matrix (40):
   {agent} × {bare, +UACP}, objective task oracles + governance metrics (rework rounds,
   evidence completeness, scope drift, cost). This is what makes the telos's **friction
   budget** empirically measurable (`design/telos/40-derivations.md` names this substrate as
   the source of its quantitative proxy).

Two readouts, not two systems: the benchmark is the test run *scored*; the test is the
benchmark run *gated*.

## Why self-diagnosis was not enough (supersede + absorb)
`design/self-diagnosis` (branch `docs/self-diagnosis-design`) got the **observer** right —
content-independent L1–L4 mechanism properties, fail-closed CODE gates (never an LLM judge),
the decoupling litmus, mandatory planted-fault calibration. It is absorbed nearly verbatim
into 30.

What it could not deliver was the **driver**: two manually-coordinated Claude contexts, no
plugin/MCP tool surface, and its own open precondition — *"whether a plain `claude` session can
drive the lifecycle here; the `uacp_*` governed writers were not present."* A scripted,
in-process drive proves the engine can be *called*; it does not prove an agent can *consume the
product*. The Proving Ground replaces that driver with a real contained agent hitting the real
tool surface — which is exactly the standing gap: governed runs cannot be driven from sessions
where the plugin is not loaded, and nothing today proves the loaded surface end-to-end.

## Placement
This is **operational tooling, not kernel**: it consumes UACP as a black box and must stay
outside the observed system (the observer cannot be part of the observed — 10). It is also the
**first consumer** of the neutral-runner layer (20), which is useful beyond benchmarking
(dispatching any agent over one transport).
