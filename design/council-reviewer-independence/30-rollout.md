---
type: roadmap
title: Rollout — correctness first, then teeth, then vocabulary
description: Sequencing for the bundle. Slice 1 (load-bearing correctness) = minimal-non-leading dispatch + the two hard-break fixes + rendering rule + audit-loop rewrite + locking tests; the committed, buildable design. Slice 2 (teeth, DEFERRED) = grounding_provenance, which does not yet work as designed (diff-echo + MCP-hollow) and un-defers only under stated conditions. Slice 3 (vocabulary, DEFERRED with Slice 2) = the pull dimension in the canonical taxonomy. Revised 2026-07-10 after a 3-reviewer audit — teeth deferred-until-honest per decision.
tags: [rollout, sequencing, slices, advisory-first, council-gate]
timestamp: 2026-07-10
edges:
  - {dst: 10-minimal-non-leading-dispatch, rel: sequences, provenance: asserted}
  - {dst: 11-grounding-provenance, rel: sequences, provenance: asserted}
---

# Rollout

## Slice 1 — correctness (load-bearing; ship first)

The fix that must land before or with any reduction in what is pushed, so the reviewer is never
starved ([[01-narrative-vs-spec]]):

- Plumb `context_policy: minimal-non-leading` into Tier >=2 `review`/`audit` dispatch with the
  retain-vs-strip contract ([[10-minimal-non-leading-dispatch]]).
- Fix the two HARD breaks ([[20-blast-radius]]): the debate phase-1 sole-task-line, and the
  deep-research/ultracode empty-query.
- Apply the empty-narrative rendering rule everywhere the narrative is stripped.
- Land the three Slice-1 locking tests ([[20-blast-radius]] tests 1–3: projection / debate / workflow),
  at minimum test 1 (projection strips narrative, keeps a resolvable change pointer; Tier 0/1 untouched).
  Test 4 (grounding_provenance fail-close) is **not** a Slice-1 gate — it ships with Slice 2's teeth.

Slice 1 also includes the **audit-loop doc rewrite** ([[21-audit-loop-rewrite]]) — it depends only on the
narrative-vs-spec distinction, not on the teeth, so it lands here — and the Slice-1 (prompt-only)
**domains floor-not-ceiling** instruction ([[12-domains-coverage-floor]]). Slice 1 strictly improves
independence (removes the leading narrative) **without** the teeth, and is safe to ship alone — it does
not overclaim, because it does not assert `pull` in `diversity_sources` (that would require the deferred
Slice 2 check).

## Slice 2 — teeth (DEFERRED; does not yet work)

`grounding_provenance` ([[11-grounding-provenance]]) is **not built with Slice 1**. As first sketched it
cannot distinguish self-pull from restated-push (diff-echo) and is environmentally hollow on the preferred
MCP path. It un-defers only when the three conditions in [[11-grounding-provenance]] hold: path-scoped pull
credit (CLI/contained only), evidence-beyond-the-pushed-diff, and a planted-fault calibration fixture
(mandatory before any flip to fail-closed). Revisit when a real dogfood finding shows blind/confabulated
reviews actually occur, or when Tier-3 environmental containment makes the field defensible.

## Slice 3 — vocabulary (DEFERRED with Slice 2)

- **NOW:** the documentation-only half of [[13-taxonomy-dimension]] — name the "runtime-swap ≠ independence"
  fallacy (no enforcement claim). And the *recording* of derived-vs-pushed domain divergence in output
  ([[12-domains-coverage-floor]]) waits with the teeth.
- **DEFERRED:** adding `pull` as a first-class Diversity Dimension in the canonical `council-taxonomy.md`
  and recording it in `diversity_sources` — gated on the Slice 2 check passing, so `pull` is never
  asserted without the teeth that make it truthful. Serializing canonical vocabulary earlier would be
  premature.

## Cross-provider council (2026-07-10)

The design was reviewed by a genuine cross-provider council — Codex (OpenAI), Gemini (Google), Kimi
(Moonshot), each dispatched read-only with a scope-pointer-only prompt (no leading narrative, no prior
findings — dogfooding this bundle's own pull thesis). **Unanimous verdict: SOUND-WITH-GAPS; safe to build
Slice 1 provided it is framed as dispatch hygiene, not achieved independence.** All three independently
re-verified the factual spine against source (context_policy unwired, no pull/push axis, MCP-no-cwd,
diff-in-prompt, both hard breaks, no guarding test, honest teeth deferral).

New findings folded into the bundle:
- **Cross-runtime domain-expansion gap** (Gemini) → [[12-domains-coverage-floor]]: `cross_domain_signals`
  is Layer-2 (intra-bridge) only; no orchestrator mechanism propagates a discovered domain across runtimes.
- **"Claude Layer-2 is debate" overstated** (Codex) → [[20-blast-radius]]: Claude uses Workflows/Task Tool
  by tier/mode; the debate break is path-specific.
- **Round-1 domains anchor before signals fire** (Kimi) → [[12-domains-coverage-floor]].
- **Slice-1-is-hygiene-not-independence** (all three) → [[00-problem]] + [[10-minimal-non-leading-dispatch]].
- Reconciled to a **false positive** (source decides): Kimi's "minimal-non-leading misattributed to
  uacp-council" — the discipline IS in `uacp-council/references/modes.md:16-20`; Kimi grepped the literal
  token and missed the prose. Grain of truth (enum mechanism lives in bridge/debate) folded into
  [[10-minimal-non-leading-dispatch]].

## Governance

`council-taxonomy.md`, `uacp-bridge/SKILL.md`, and the council phase docs are canonical/kernel-adjacent
(Authority Chain layers 2–3). Per Key Invariant #4, the *build* still requires **council review before
PLAN exits**, zero material findings unresolved. This design-stage cross-provider council is the
pre-governance equivalent; once Slice 2 exists, such a review should itself produce resolvable
`grounding_provenance` (the design dogfooding its own teeth).

## Status / Checkpoint

**2026-07-10** — Bundle drafted → revised after a 3-subagent (same-model) review (teeth deferred-until-honest)
→ revised again after a **cross-provider council** (Codex/Gemini/Kimi): unanimous SOUND-WITH-GAPS, safe to
build Slice 1 as hygiene. Their new findings folded in (cross-runtime domain gap, Claude-Layer-2 precision,
Round-1 anchoring, hygiene-not-independence framing); one finding reconciled to a false positive against
source. Nothing built. No PR. Slice 1 is the buildable design (framed as hygiene + break-fixes); Slices 2–3
recorded-but-deferred. Next: decide whether to commit the bundle, then — if building — a governed council
review of the Slice-1 canonical-doc changes before PLAN exits.
