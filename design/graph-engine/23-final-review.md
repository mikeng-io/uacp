---
type: analysis
title: Graph Engine — Final Delta Review (internal delta-council + external Codex)
description: Pre-build gate. 3 internal Opus delta-lenses (storage, context-loop, spike-validity) + 1 external Codex review. All CONCERNS; design SOUND, but build-facing contract nodes still describe superseded decisions. Convergent findings + remediation + the v1 reframe.
tags: [graph-engine, review, gate, pre-build]
timestamp: 2026-06-20
edges:
  - {dst: 02-decisions, rel: decides_on, provenance: asserted}
---

# Final Delta Review — pre-build gate (2026-06-20)

4 reviewers: internal Opus delta-lenses (storage/data-model, context-loop, spike-validity) + **external
Codex** (different model family — independence check). **All four: CONCERNS.** The external review
**independently matched** the internal top findings → low shared-blind-spot risk.

**Verdict:** the core design is **sound — build it**. The bundle is **not yet a safe build *contract***
because build-facing nodes still describe superseded decisions. Work left = doc reconciliation + a
sharper v1 scope, **not redesign.** Codex's reframe: *"this is not a 'graph engine' v1; it's a manifest
schema fix + a read-only closure projector."*

## Convergent findings (multiple reviewers)

**T1 — BLOCKER — stale contract nodes (ALL 4 reviewers).** Ledger says files+in-memory (D29) + clean
break (D32), but **nodes 14, 19, 19a** still instruct building **SQLite + sqlite-vec + Index port**, and
**D20 / 20-slices** still mandate the **compat-shim D32 retired**. Fix: make D29/D32 the live contract
*everywhere* — banner/rewrite 19, 19a; widen node-14's banner over `## Build` + `## Index port`; strike
the shim from D20 verdict + 20-slices; one statement of v1 scope.

**T2 — phase-aware closure severity (3/4, incl. external).** `unverified` is expected mid-run; only a
BLOCK at the relevant phase-exit. Split checks: **structural (always-block)** vs **progress
(phase-gated by Heartgate)**. Fold into D26 / 14.

**T3 — green graph ≠ correct work (2/4).** Closure proves *coverage topology*, not decomposition
correctness; an `asserted derives_from` to a real-but-wrong scope_item passes. Make PROPOSE→PLAN council
a **hard gate** with a review artifact over every asserted edge; re-review on asserted-edge target change.

## New / sharp (external + spike lens)

**T4 — the WRITER is the real bottleneck, not the projector (Codex).** Split v1:
- **Phase A** = schema fix (two keys) + **read-only closure projector** (cheap, safe; ~already done by
  the spike).
- **Phase B** = entity writer + formatter + validator + **Guardian raw-write block** + id minting +
  `_index.yaml` handling. The graph is NOT trustworthy until raw manifest writes are actually blocked.
Don't ship Phase A claiming trust it doesn't have.

**T5 — spike-integrity (internal spike lens).**
- Legacy "9 uncovered / 2 orphan / 0 edges" headline is **not reproducible in this worktree** (legacy
  fixtures absent) → commit the legacy fixtures under `spike/` OR restate as "measured vs main @ <sha>".
- New-form fixtures were **never run through the real `validate_uacp_artifacts.py`** → "passes
  validate-on-write" is asserted, not shown. (Also: partial/phantom/inprogress fixtures lack
  `out_of_scope` → would fail line 438.) Run the validator over `oauth-login/proposal.yaml` as proof.
- `unverified` marks a work_unit "verified" even when its assessment `result: fail` → the kernel
  verify-check must AND-in `result == pass`; add a `contradicted` fixture.

**T6 — node/file granularity over-applied for v1 (Codex + storage).** 11-node-taxonomy says one-file-
per-entity, but D20 says "no entity re-layout beyond the two keys." For v1: keep the existing aggregate
YAML shape, just add ids + `derives_from`. Entity-per-file is a later (Phase B) write-blast-radius win.

## Deferred (not v1, but capture before ratifying)

**T7 — context-loop (D30/22) duplicates the AS-BUILT corpus (context lens).** `corpus.py`,
`Lesson`/`KnowledgeItem`, 2-tier `lessons→knowledge` promotion, `promoted_to`, BES scorer +
`[memory.distillation]` already implement ~70%. D30/22 read greenfield with a parallel vocabulary
(`fact/lesson/procedure` + 4 tiers + undefined "evidence strength" vs BES). Add a "Reconciliation vs
as-built corpus" section (reuse/extend/supersede per element) before D30 is treated as ratified. Also:
`derived_from` (knowledge grounding) vs `derives_from` (scope coverage) vs corpus `derived_from` —
three near-identical keys; register distinctly in the schema.

**T8 — minor:** D24 watermark/STALE-BLOCK is **dormant** in the recompute-on-read v1 (nothing can be
stale) — note it activates only with the deferred SQLite cache. Node 11 `## Aggregates` predates D28
(no canonical/derived split) — one sentence. `partial` findings-table row omits `unverified=1`.

## Remediation order

1. **Reconcile contract nodes** to D29/D32 (T1) — the dominant, unanimous fix; an implementer must not
   read superseded SQLite/shim text. (Pure doc edits.)
2. **Reframe v1** (T4): rename scope to "manifest schema fix + read-only closure projector"; the writer/
   Guardian is **Phase B**. Update 20-slices.
3. **Phase-aware closure** (T2) into D26/14.
4. **Spike integrity** (T5): self-contained fixtures + actually run the validator + fix the vacuous
   `unverified`.
5. **Capture** T3 (council hard gate), T6 (no re-layout v1), T7/T8 (deferred reconciliations).

None blocks the *idea*; all block treating the *bundle* as a ratified build contract. Fix 1–4, then build Phase A.
