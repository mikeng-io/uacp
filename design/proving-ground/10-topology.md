---
type: analysis
title: Topology — the SUT container, the outside runner/observer, and the host model
description: The agent + the UACP runtime live INSIDE the system-under-test container; the runner and observer live OUTSIDE the jail (the observer cannot be part of the observed). The model is served on the macOS HOST (ollama, Metal — containers on a Mac cannot reach the GPU) and reached from the container via host.docker.internal; cloud cells differ only in egress policy. Cells are swapped by swapping the agent container; runner + observer never change. Isolation ladder — Docker now; libkrun/Apple-container for microVM-grade later; Firecracker only on a Linux runner (no KVM on macOS).
tags: [topology, container, isolation, sut, host-model, egress, observer-external]
timestamp: 2026-07-17
edges:
  - {dst: 00-proving-ground, rel: depends_on, provenance: derived}
---

# Topology

```
┌─ SUT container (per cell) ───────────────────────────────────────────┐
│  agent runtime (Claude Code | Hermes | …)                            │
│  ± UACP runtime (plugin / MCP server / Guardian hooks) — the product │
│  task workspace (fresh git clone, pinned task)                       │
│  egress: cloud cell → provider API only | local cell → host model    │
└────────────────────────────▲─────────────────────────────────────────┘
                    ACP stdio │ (the one transport, crossing the boundary)
┌────────────────────────────┴─ host / control plane (OUTSIDE the jail) ─┐
│  RUNNER  — spawns the container, injects the task, drives over ACP     │
│  OBSERVER — reads ONLY the emitted trail (gate ledger, .uacp/state,    │
│             git log, transcript, hook log) → L1–L4 → verdict + scores  │
│  MODEL   — ollama on macOS host (Metal) at :11434                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## The three placement rules
1. **UACP lives WITH the agent, inside the SUT container.** It is the thing the agent
   consumes; a ±UACP cell is literally the same container with the plugin surface toggled.
2. **The observer lives OUTSIDE and reads only what leaked out.** A witness inside the sandbox
   it grades is the self-attestation the framework forbids (same law as "no self-attesting
   closure"; inherited verbatim from self-diagnosis: *the observer cannot be part of the
   observed*). The runner is outside for the same reason — the SUT must not be able to drive
   its own driver.
3. **The model lives on the HOST.** Linux containers on macOS cannot reach the Metal GPU, so a
   35B-class local model in-container is not viable; the host serves it (ollama, Metal) and the
   container reaches it at `host.docker.internal:11434`. A cloud cell (Claude Code) is
   topologically identical — only the egress allowlist differs (provider API instead of host
   model). This is the one structural concession to running on a MacBook, and it is measured:
   the model is shared infrastructure, the *workspace* is what isolation protects.

## Isolation ladder (decided posture)
- **Now: Docker** (present, running) — namespace/fs/network isolation; matches the containment
  the e2e-acceptance design already assumes; sufficient for a messy-but-not-hostile coding
  agent, and OpenAB's per-agent Dockerfiles land on it directly (20).
- **Later, if kernel-grade isolation is wanted on Apple Silicon:** libkrun/krunvm or Apple's
  `container` (Hypervisor.framework microVMs) — the actual "Firecracker on a Mac" answer.
- **Firecracker proper: only on a Linux runner** (needs /dev/kvm; macOS has none and Apple
  Silicon offers no nested virt) — a CI-matrix option, never a local requirement.

## Per-cell egress policy
Egress is part of the cell definition and enforced at the container boundary:
`claude-bare/claude-uacp` → Anthropic API only; `hermes-local-*` → host model only;
nothing else (no package registries mid-run — images are pre-baked, 20). A cell that needs an
exception declares it in its manifest; undeclared egress is a finding, not a config error.
