---
type: design
title: Domains as a coverage floor, not a suspect ceiling
description: The pushed `domains` array frames the audit (a real auditor isn't handed the list of departments to suspect). Rather than strip it (it is load-bearing for role dispatch), reframe it as a minimum coverage floor the reviewer must meet AND exceed — requiring the reviewer to emit its own independently-derived domains via the existing cross_domain_signals mechanism and flag divergence from the pushed set.
tags: [domains, coverage-floor, cross-domain-signals, scope, independence]
timestamp: 2026-07-10
edges:
  - {dst: 10-minimal-non-leading-dispatch, rel: extends, provenance: derived}
  - {dst: 11-grounding-provenance, rel: relates_to, provenance: asserted}
---

# Domains as a coverage floor

## The residual tell

[[10-minimal-non-leading-dispatch]] strips the leading narrative but keeps the `domains` array
pushed. That array is a real, if subtler, tell: an orchestrator that says "examine security,
concurrency, data-integrity" has already framed the audit. A genuine Deloitte engagement is not
handed the list of departments to suspect — the auditor decides where to look. And in Tier 2 the
domains are computed by the *same orchestrator that planned the work*, so a blind spot in planning
becomes a blind spot in the "independent" audit.

## Why not just strip it

`domains` is load-bearing: one expert prompt per domain, `DOMAIN: {domain}` in the template,
`domains_covered` in the output, focus-areas/standards resolution. Removing it collapses the role
structure. The fix is not removal — it is **reframing what the array means**.

## The reframe

Treat the pushed `domains` as a **coverage floor, not a suspect ceiling**:

- The reviewer MUST cover at least the pushed domains (the floor guarantees baseline coverage — a
  reviewer that ignores security because it "didn't think to look" is worse than one told to).
- The reviewer MUST **independently derive its own domains from the artifact** and add any the
  orchestrator did not list — via the **already-existing `cross_domain_signals`** mechanism
  (`uacp-bridge` between-rounds domain expansion), which is exactly the channel for "another domain
  should examine this."
- The reviewer MUST **flag divergence** — domains it judged irrelevant, and domains it added that the
  orchestrator missed. That divergence is itself a high-value signal (a planning blind spot surfaced
  by the independent reviewer).
- The pushed list must be derived from triage/artifact scope, **not** from the author's risk
  narrative (that would re-import the leading narrative through the domains channel).

Be candid about the ceiling: this is **instruction-tier** only. Telling the auditor "cover at least
security, concurrency, data-integrity" still plants the orchestrator's suspicion set, and "also look
elsewhere / flag divergence" does not un-plant it — divergence-flagging is itself unverifiable until the
teeth exist. So the reframe is a real improvement on coverage but only a partial one on independence; it
is honest to say so rather than call it a full fix.

**Two mechanism limits surfaced by the cross-provider council (2026-07-10) — do not overstate what
`cross_domain_signals` buys:**

- **It is Layer-2 (intra-bridge) only.** `cross_domain_signals` expands the council *inside one runtime*
  (the uacp-bridge two-layer architecture: Layer 2 = intra-bridge, Layer 1 = cross-bridge synthesis). The
  `uacp-council` orchestrator has **no mechanism to propagate a domain that Runtime A discovered to
  Runtime B** during a Tier 2/3 council. So a domain the independent reviewer surfaces is examined only by
  that one runtime — independence is bottlenecked by "the first runtime that thinks to look." A genuine
  cross-runtime coverage-floor would need a Layer-1 domain-expansion loop that does not exist today; that
  is out of scope for this node and flagged as a follow-up, not claimed as delivered.
- **Round-1 experts see the pushed domains first.** Experts receive the pushed `domains` in Round 1
  *before* they can emit any `cross_domain_signals` (which only feed the next round). So Round 1 is anchored
  on the orchestrator's set regardless; the "derive your own" correction only takes effect from Round 2 on.
  The floor-not-ceiling framing is therefore weaker in Round 1 than the prose above implies — state it
  plainly rather than imply the reviewer self-scopes from the start.

## Slicing

Two parts, matching the bundle's rollout:

- **NOW (Slice 1, prompt-only):** the floor-not-ceiling instruction in the external-reviewer dispatch —
  "cover at least these domains; independently derive and add any others; flag what you judged
  irrelevant." `cross_domain_signals` already exists and already triggers domain expansion, so this is
  prompt wording, no new schema.
- **DEFERRED (with [[11-grounding-provenance]]):** *recording and crediting* derived-vs-pushed domain
  divergence in the output — an added domain is credible only when its finding carries a retrieval trail
  that survives the (deferred) provenance check, not a bare assertion that "this area also matters."
  Until then, divergence is surfaced but not certified.
