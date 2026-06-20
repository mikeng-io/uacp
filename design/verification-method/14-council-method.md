---
type: design
title: The Council Method — the Agent Council as a generative-gate panel
description: Recast Agent Council verification from "re-read and opine" to a disciplined generative-gate panel — enumerate targets from the content, assign one verifier per target, give each a distinct lens, default-to-refute, and require a majority to clear. Adopts the vendored code-review skill's severity tiers + review flow.
tags: [verification, council, adversarial, diverse-lens, severity-tiers]
timestamp: 2026-06-21
edges:
  - {dst: 10-generative-gate, rel: depends_on, provenance: derived}
---

# The Council Method

## The problem it fixes

Today the Agent Council can drift into "re-read the artifact and give an opinion" — unbounded, redundant, and non-reproducible (a human-judgment version of #503's weak proxy). The fix: make the council a **panel that runs the [generative gate](10-generative-gate.md)** — its findings are generated from content and serialized, not free-form prose.

## The method

1. **ENUMERATE** targets from the manifest/diff (not a vibe of "review it").
2. **ASSIGN one verifier per target** (coverage is structural — closes #503 class D).
3. **DIVERSE LENS** — when a target can fail in more than one way, give each verifier a *distinct* lens (correctness / security / reality-binding / does-it-reproduce) instead of N identical reviewers.
4. **DEFAULT-TO-REFUTE** — each verifier tries to *refute*; a finding clears only on a **majority** that fails to refute (adversarial verify — prevents plausible-but-wrong passes).
5. **SERIALIZE** verdicts into the [investigation ledger](13-investigation-ledger.md) with provenance.

## Adopts the vendored `code-review` skill
- **Severity tiers**: `[blocking]` / `[important]` / `[nit]` map onto the gate's BLOCK / warn / note.
- **The 4-phase review flow** (context → high-level → line-by-line → decision) seeds the council's enumerate→route order.
- One-directional reference (ADR-0017): the council method *references* `skills/code-review`; it does not copy it. (Backlog T-003 wires the phase skills.)

## To expand
- The panel sizing rule (verifiers per target by risk/phase), tied to the harness's adaptive depth.
- Neutrality: keep council as a verification *body*, never a state database (planes separation) — it emits findings, the kernel records state.
- Wiring into `uacp-council` / `uacp-debate` (file-based round-state, sub-agent neutralized).
