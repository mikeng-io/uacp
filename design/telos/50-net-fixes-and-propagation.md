---
type: decision
title: Net-fixes and propagation — the #98 leftovers, the ADR, and CMS-bundle reconciliation
description: The remaining #98 "fix the net" items folded in (authority chain -> one canonical; missing first-principles axioms; human-verdict primitive; deterministic-vs-semantic gate taxonomy; context-model artifact; UACP.md<->bundle sync). Plus the landing plan — an ADR superseding ADR-0018, propagation to AGENTS.md + UACP.md, a decision-log entry, and how THESE telos nodes reconcile INTO the CMS bundle on the governed #98 build (not beside it).
tags: [net-fixes, authority-chain, first-principles, human-verdict, gate-taxonomy, propagation, adr, "issue-98"]
timestamp: 2026-07-16
edges:
  - {dst: 00-telos, rel: decides_on, provenance: asserted}
---

# Net-fixes and propagation

## A. The #98 "fix the net" items (folded in)
Each is a bedrock-coherence gap from the audit; the telos supplies or scopes the fix.

1. **One authority chain.** Two competing chains exist — `AGENTS.md`'s table vs
   `constitution.md:196-209`. Pick ONE canonical (the `AGENTS.md` priority table is the
   operative one) and demote the other to a pointer, recorded via a **decision-log entry** (the
   only sanctioned override mechanism). No new chain is introduced here.
2. **Missing first-principles axioms.** `first-principles.md`'s "Derives from" clauses cite
   principles that do not exist there. The **telos is that missing first principle** — write it
   (the conformance-loop + semantic differentia) and re-point the dangling "Derives from"
   clauses at it. Strip vendor specifics from `first-principles.md` while there.
3. **Human-verdict primitive.** Model the human verdict in loop terms: it is a **base case**
   (20.3) — *exempt from measure/evaluate-discipline* (a human may decide without a decidable
   signal) but **never exempt from serialize-discipline** (the verdict must be recorded,
   provenanced, hinge-side). Add a minimal typed shape so a human decision is a first-class,
   auditable serialization, not an off-ledger act.
4. **Deterministic-vs-semantic gate taxonomy.** Name the two gate kinds and their trust rule:
   a **deterministic** gate is trusted by construction (codeflair witness / diff / test); a
   **semantic** gate (council / LLM evaluation) is trusted only via **recursive critique to a
   base case** (20). This node makes explicit which gates are which, so no semantic gate is
   silently treated as deterministic.
5. **Context-model artifact.** Give Comprehend an artifact: a minimal `uacp.context_model`
   (the "Model" of 30) with a **re-comprehension vs re-interpretation** rule — comprehend once,
   do not silently re-interpret downstream (the cooperation case: two actors share one Model).
   Scoped here; schema is a build task.
6. **UACP.md ↔ bundle sync.** `UACP.md` (the injected cognition) drifted from its bundle
   (superseded "decision-bearing" wording; "CMS at every grain" with no base case). Add a
   **sync check** and fix the wording so the running agent's preamble and the canonical bundle
   cannot silently diverge.

## B. How this lands (propagation)
On the governed **#98** build (worktree → PLAN → council → EXECUTE), these DRAFT nodes reconcile
**into** the canonical surfaces — they do not ship as a parallel bundle:

- **CMS bundle** (`design/comprehend-measure-serialize/`):
  - `00-the-axiom.md` → reframed to derive from the telos (CMS = the discipline chosen to serve
    the purpose; the purpose is 00-telos here);
  - `11-measure.md` → renamed/rescoped to **Evaluate** (30); the fail-closed content is kept;
  - `21-decision-hinge.md` → gains the Evaluate/Decision split (30) and the recursive-critique
    attachment (20);
  - `23-composition.md` → gains the **grain base case** (40) that closes its "no base case";
  - **new nodes** absorbed from here: the telos (00), recursive critique (20), the gate taxonomy
    (A.4), the human-verdict primitive (A.3).
- **ADR** — supersede/amend **ADR-0018** (cms-semantic-thinking-principle) with the decision:
  *the telos is primary; CMS/gates/lifecycle/memory derive from it; recursive-critique + base
  case is the third leg; measure→evaluate.*
- **`AGENTS.md`** Core Principle — sync to the reframed pipeline + the conformance-loop framing.
- **`UACP.md`** — carry the reframe + the base case (A.6); it is the cognition the agent runs on,
  so the words here must match the bundle.
- **`docs/INDEX.md`** — place the telos in the canonical read order (bedrock-priority).
- **Decision-log** — one entry recording the authority-chain choice (A.1) and the ADR-0018
  supersession.

## C. Governance note
This touches **canonical docs** → Invariant #4 (council gate) applies; it must run through the
lifecycle with a cross-provider council before it merges. This bundle is the **pre-governance
design input** (`governance: pre-governance-input`) — the red-pen artifact, not the merge.
