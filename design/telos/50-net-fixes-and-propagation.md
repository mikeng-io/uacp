---
type: decision
title: Net-fixes and propagation — the #98 leftovers, the cooperation rule, the To-expand sweep, and the ADR
description: The remaining #98 "fix the net" items folded in (authority chain -> one canonical; the missing first principle written and constitution.md's dangling "Derives from" clauses re-pointed; human-verdict primitive; deterministic-vs-semantic gate taxonomy; context-model artifact + the CROSS-ACTOR rule; UACP.md<->bundle sync). Adds the CMS-bundle "To expand" SWEEP (#98's exit line) — every item written-or-deferred-with-owner. Landing plan — an ADR amending ADR-0018 (which KEEPS `measure` per mike's reaffirmed ruling), propagation to AGENTS.md + UACP.md, a decision-log entry, and reconciliation INTO the CMS bundle.
tags: [net-fixes, authority-chain, first-principles, human-verdict, gate-taxonomy, cooperation, to-expand-sweep, propagation, adr, "issue-98"]
timestamp: 2026-07-16
edges:
  - {dst: 00-telos, rel: decides_on, provenance: asserted}
---

# Net-fixes and propagation

## A. The #98 "fix the net" items
Each is a bedrock-coherence gap from the audit; the telos supplies the fix or scopes it
honestly (fixed-here vs deferred-with-owner is marked per item).

1. **One authority chain.** *(fixed here — decision)* Two competing chains exist:
   `AGENTS.md`'s 5-row table vs `constitution.md`'s 8-level Authority Chain (~lines 162–183).
   Decision: the **`AGENTS.md` priority table is canonical**; `constitution.md`'s chain is
   demoted to a pointer at it. Recorded via a **decision-log entry** (the only sanctioned
   override mechanism). No third chain is introduced.
2. **The missing first principle.** *(fixed here — content; edits at build)* The dangling
   "Derives from" clauses live in **`constitution.md`** (its chain and article derivations cite
   `first-principles.md` for principles that do not exist there — `first-principles.md` is the
   *cited target*, not the citer). Fix: write the telos (00/10 — the conformance loop + the
   semantic differentia) INTO `first-principles.md` as the missing principle, re-point
   `constitution.md`'s clauses at it, and strip vendor specifics from `first-principles.md`
   while there.
3. **Human-verdict primitive.** *(framing fixed here; typed schema deferred — owner: #154)* The human verdict is the **critique base case #3** (20): explicitly a
   serialized-fiat exception — exempt from measure-discipline, never from serialize-discipline
   (recorded, provenanced, hinge-side). The build adds a minimal typed shape so a human decision
   is a first-class, auditable serialization, not an off-ledger act.
4. **Deterministic-vs-semantic gate taxonomy.** *(fixed here — rule; per-gate labeling at
   build)* Two gate kinds, two trust rules: a **deterministic** gate is trusted by construction
   (codeflair witness / diff / test); a **semantic** gate (council / LLM evaluation) is trusted
   only via **recursive critique to a critique base case** (20). The build labels each existing
   gate so no semantic gate is silently treated as deterministic.
5. **Context-model artifact + the cross-actor rule.** *(rule fixed here; schema deferred —
   owner: #154)* Comprehend gets an artifact: a minimal `uacp.context_model`
   — the serialized **Model** of 30. The **cooperation rule** (the telos's central noun,
   mechanized): when work crosses actors, the second actor **consumes the serialized Model and
   the declared intent — never re-interprets raw reality behind the first actor's back.**
   Re-comprehension (rebuilding the Model from reality, *declared and serialized as such*) is
   legitimate; silent re-interpretation is the cross-actor drift the loop exists to prevent.
   The hand-off of the binding IS the unit of cooperation; this is what makes "friction of
   cooperation" (00) concrete: without the rule every hand-off pays the re-derivation tax and
   risks divergent Models.
6. **UACP.md ↔ bundle sync.** *(intent fixed here; mechanism deferred — owner: #154, as a
   lint/CI check)* `UACP.md` (the injected cognition) drifted from its bundle
   (superseded "decision-bearing" wording; "CMS at every grain" with no base case). The build
   fixes the wording (grain base case, 40) and adds a sync check so preamble and bundle cannot
   silently diverge.

## B. The CMS-bundle "To expand" sweep (#98's exit line)
#98's exit requires **every** remaining "To expand" in the CMS bundle written-or-deferred-with-
owner. Disposition of all eleven:

| Node | To-expand item | Disposition |
|---|---|---|
| 10-comprehend | context-model artifact / comprehension discipline | **Written here** — A.5 (schema at build) |
| 11-measure | signal taxonomy (PASS/FAIL/ERROR grades, evidence classes) | **Deferred — owner: #154** (doc task; no design fork) |
| 12-serialize | serialization targets / "not a Memory framework" tension | **Written here** — resolved by the *substrate* reframe (00, 30) |
| 20-reductions | more capability-reduction examples | **Deferred — owner: CMS bundle maintenance** (illustrative, non-blocking) |
| 21-decision-hinge | routing-table-as-data | **Deferred — owner: #154** (mechanical; 30's split is the design) |
| 22-differentia | sharpen vs adjacent frameworks | **Written here** — 10's semantic differentia + honest limits IS that sharpening |
| 23-composition | grain base case | **Written here** — 40 (grain base case = the governed write) |
| 23-composition | cross-run axis | **Written here** — 30 (feedback edge = the substrate); enforcement at build |
| 24-phase-crosswalk | per-phase CMS crosswalk gaps | **Deferred — owner: #154** (sync with 10's honest limits: TRIAGE/BRAINSTORM upstream) |
| 25-enforcement-surfaces | sync-check between surfaces | **Written here** — A.6 (mechanism at build) |
| 30/31 (validation/instantiations) | refresh matrix + instantiation list post-reframe | **Deferred — owner: #154** (bookkeeping after the merge) |

Nothing is left silent: every item is written here or carries a named owner.

## C. How this lands (propagation)
On the governed **#98** build (worktree → PLAN → council → EXECUTE), these nodes reconcile
**into** the canonical surfaces — they do not ship as a parallel bundle:

- **CMS bundle** (`design/comprehend-measure-serialize/`):
  - `00-the-axiom.md` → gains the derivation: CMS is the discipline chosen to serve the telos;
    "coherence is the product" **stands** (00 here supplies the why, it does not contest the
    what);
  - `11-measure.md` → **unchanged in name** (mike's ruling reaffirmed 2026-07-17); gains a
    pointer to 30's "the operation is a judgment; the name is the intervention" statement;
  - `21-decision-hinge.md` → gains the Measure/Decision critique-attachment (30), with Decision
    kept as the seam-box, not a fourth verb;
  - `23-composition.md` → gains the **grain base case** (40);
  - **new nodes absorbed**: the telos (00), the conformance loop (10), recursive critique (20),
    the gate taxonomy (A.4), the human-verdict primitive (A.3).
- **ADR** — **amend** ADR-0018 (not supersede-and-replace): add the telos derivation, recursive
  critique + the critique base case, the grain base case, the substrate reframe — and
  **re-affirm** its `measure` naming decision (30 records the v1 rename attempt and its
  rejection, so the question does not silently re-open a third time).
- **`AGENTS.md`** Core Principle — sync: conformance-loop framing, the differentia headline,
  the substrate wording; CMS text stays (names unchanged).
- **`UACP.md`** — carry the grain base case + the sync fix (A.6); names unchanged.
- **`docs/INDEX.md`** — place the telos in the canonical read order (bedrock-priority).
- **`first-principles.md` / `constitution.md`** — A.2 (write the principle; re-point the
  clauses; demote the duplicate chain per A.1).
- **Decision-log** — one entry: authority-chain choice (A.1) + ADR-0018 amendment + the two
  mike rulings this v2 encodes (memory→substrate; `measure` stays).

## D. Governance note
This touches **canonical docs** → Invariant #4 (council gate) applies; it must run through the
lifecycle with a cross-provider council before merge. This bundle is the **pre-governance
design input** (`governance: pre-governance-input`) — v2, post-panel (2× adversarial/
completeness + cross-provider gemini; findings folded 2026-07-17). The red-pen artifact, not
the merge.
