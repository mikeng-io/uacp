---
type: decision
title: Rollout + settled decisions (reconcile-then-enforce) + ADR-0020
description: The reconcile-then-enforce staged rollout (so a hard gate never lands on an unvalidated corpus as a red wall), the four settled scoping decisions, and the ADR-0020 pointer. Carries this bundle's own Status/Checkpoint (dogfooding the pattern).
tags: [uacp-design, rollout, decisions, adr, checkpoint]
timestamp: 2026-06-26
edges:
  - {dst: 00-intent, rel: decides_on, provenance: asserted}
  - {dst: 21-lint, rel: sequences, provenance: asserted}
  - {dst: 20-skill, rel: sequences, provenance: asserted}
---

# Rollout + settled decisions

## Settled decisions (mike, 2026-06-26)

1. **ADR — yes.** This gets **ADR-0020**, establishing the design-bundle convention + the
   skill/lint split (as ADR-0017 did for skills).
2. **Lint coverage — validate ALL `design/**`, staged.** Not new-only. But via reconcile-then-enforce
   (below), because the live corpus has never been gated.
3. **Status/Checkpoint — SOFT.** Skill-recommended, lint does NOT require it; the lint only validates
   its *shape if present* ([21](21-lint.md) check 7). No retroactive flag.
4. **Node `type` taxonomy — DERIVED, not invented; CORE settled, closure DEFERRED.** The CORE set is
   derived from the audit ([10](10-taxonomy-audit.md)): `analysis | design | contract | reference |
   decision | pattern`, reconciling `design-node → design`. What is **settled** is the *method*
   (derive-don't-invent) + the **two-tier** check (hard-fail missing/malformed `type`, warn-only on
   unknown). What is **deferred** (NOT settled): whether to *close* the vocabulary and how to dispose
   of the one-offs (`roadmap`/`lessons`/`evidence`) — `evidence` is likely admitted, not folded (the
   framework's evidence thesis). That decision waits for the REPORT pass. *(So this node and
   [10](10-taxonomy-audit.md) agree: core derived, closure open.)*

## Reconcile-then-enforce rollout (the whole point of "validate all" not being a red wall)

1. **REPORT** — land the lint in report-only mode; run it over all `design/**`; produce the violation
   inventory (expected from the audit: 1 `_index.md`, the `design-node` rename, the type one-offs,
   any members/edge drift).
2. **RECONCILE** — fix the cheap violations (RECONSTRUCT `work-unit-status/_index.md` = kind+members+
   edges, rename `design-node`→`design`, repair members/edges) in a focused PR; **grandfather** only
   what is genuinely not worth fixing via an explicit allowlist (the `ruff` per-file-ignores pattern
   the repo already uses). **Allowlist discipline (so the gate doesn't erode back into guidance-only):**
   each entry carries a tracking reference + a reason, and the allowlist is **itself linted for
   staleness** — an entry whose target now conforms (or no longer exists) is a failure. The allowlist
   is a debt ledger, not a silent opt-out.
3. **ENFORCE** — flip the lint **fail-closed** in CI once the corpus (minus the allowlist) is clean.
4. **DOGFOOD** — this `uacp-design` bundle is the first conformance case; it must pass before enforce.

## Build sequence (after this design is signed off)

ADR-0020 → reconcile pass (#1-2) → the lint (TDD, report-mode) → the `uacp-design` skill → flip
fail-closed (#3) → council before each merge (kernel/docs change → cross-provider reviewer).

## Status / Checkpoint

> **2026-06-26 — DESIGN (pre-build).** This bundle is itself the scoping artifact; nothing built yet.
> The audit ([10](10-taxonomy-audit.md)) is grounded in the live corpus; the four decisions above are
> settled with mike. Open sub-decision: fold-vs-keep the three one-off node types. Next: sign-off →
> ADR-0020 + the reconcile pass. (This block dogfoods the very Status/Checkpoint pattern the skill
> recommends — soft, dated, here as a node section.)
