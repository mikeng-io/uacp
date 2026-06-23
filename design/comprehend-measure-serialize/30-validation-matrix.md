---
type: analysis
title: Validation Matrix — observation → axiom by counterexample hunt
description: The open ledger that decides whether CMS is a mere observation or a true axiom. Deliberately test the reduction against foreign domains (distributed systems, databases, compilers, protocols); the principle earns "axiom" only by surviving the hunt with no clean break. Self-referential — verify the axiom the way the axiom prescribes.
tags: [primitive, validation, axiom, counterexample, falsification]
timestamp: 2026-06-21
edges:
  - {dst: 00-the-axiom, rel: decides_on, provenance: asserted}
---

# Validation Matrix

The gate between **observation** ("most workflows fit") and **axiom** ("any valid operation MUST contain all three"). You do not assert the stronger claim — you **earn it by failing to falsify it.** This node is the open ledger.

## The hunt (deliberately foreign domains)

| Domain | Reduces to CMS? | comprehend / measure / serialize | Clean, or forced? |
|---|---|---|---|
| Event sourcing | TBD | read command + state / validate invariant / append event | |
| Raft consensus | TBD | receive RPC + log / quorum + term check / commit entry | |
| Git merge | TBD | read two trees + base / 3-way diff conflict-check / write merge commit | |
| k8s reconciliation | TBD | observe actual + desired / diff / apply (write status) | |
| CPU instruction | TBD | fetch / decode | execute → writeback | |
| LLM inference | TBD | tokenize + attend / logits / sample → emit token | |
| DB transaction | TBD | read + locks / constraint check / commit \| rollback | |
| OAuth | TBD | parse grant + creds / validate + scope / issue \| deny token | |
| Human code review | TBD | understand diff / correct? secure? / approve \| request-changes | |

> Fill each row: does it reduce **without forcing**? A clean reduction is evidence; a **forced** one (contrived relabeling) is a yellow flag; a genuine break is a **counterexample** that bounds the claim. Record honestly — a found boundary is more valuable than a forced fit.

## HUNT RESULT (2026-06-24) — 3 adversarial falsifiers, convergent

**Verdict (reclassified 2026-06-24): CMS is a COHERENCE INVARIANT (architectural), not an axiom or law (empirical).** The hunt's clean, *convergent* cross-domain reductions are **evidence it is a low-friction coherence choice** — most information-processing already fits this shape, so imposing it everywhere costs little. The "boundary" the falsifiers found (pure mechanical state-moves; human actors) is **not a counterexample to a law** — no law is claimed — it marks where compliance is **normative (must be enforced), not natural**. (A later cross-provider panel — kimi + minimax, kernel-grounded — confirmed the empirical "law/primitive" framing is unfalsifiable, and the honest claim is the architectural one. → [00](00-the-axiom.md), [25](25-enforcement-surfaces.md).)

**Reductions:**

| Domain cluster | Verdict |
|---|---|
| event sourcing · Raft AppendEntries · k8s reconcile · DB txn (commit\|rollback) | **CLEAN** |
| CPU exec · LLM token-emit · constant-folding · backpressured emit | **CLEAN** |
| OAuth issue · git 3-way merge · fire-and-forget log (level-filter *is* the measure) · UI re-render | **CLEAN** |
| gossip broadcast (seen-before/newer = measure; already-seen = DROP) | **CLEAN — reinforces** |
| **human code review** | **FORCED** — the *shape* holds, but the measure-*discipline* (deterministic + fail-closed) is FALSE for a human (same diff, different day → different verdict) |
| **read-only SELECT** | **FORCED (mild)** — measure (the `WHERE` predicate) is real; serialize=API-response stretches "durable" |
| **unconditional log/replication append** | **FORCED → BREAK** — measure can only ever PASS (a wire, not a decision); an always-PASS step isn't fail-closed |
| **NOP · interrupt-flag-set · idealized cache fill** | **BREAK** — `measure = ∅` (absent, not vacuous); the only decision lives in a *neighbouring* op (the dispatcher) → attributing it is boundary-cheating |
| **HW RNG read (RDRAND)** | **near-BREAK on comprehend** — structureless input → comprehend collapses to identity |

**The convergent finding (all three): the weak verb is `measure`, never comprehend or serialize.**
- **`measure = ∅`** for pure state-moves (NOP, unconditional append, flag-set): these are *serialize-only atoms*; CMS describes them only by importing a neighbour's decision. measure is sometimes genuinely **absent**, not merely trivial.
- **`comprehend = identity`** for structureless input (RNG) — sometimes only nominal.
- **the measure-discipline (deterministic + fail-closed) is FALSE for human actors** — it must be down-scoped to "deterministic *where the actor is mechanical*."

**The resolution — and why the boundary STRENGTHENS UACP (decisive, falsifier A):** scope the law to **governed operations**, where a real fail-closed gate is *required by definition*. Then the unconditional-append/NOP "break" falls **out of scope** — it is precisely an *ungoverned, always-PASS, self-attesting write*, the very thing UACP's no-self-attestation discipline forbids. So **CMS holds as a law within UACP's governed scope** — which is all UACP needs. The universal-axiom claim was too strong; the governed-operation law is both correct and sufficient. (This is itself evidence FOR UACP: the operations that break CMS are exactly the ones UACP refuses to allow.)

**Naming (resolves node 11's open question): step 2 should be `decide`, not `measure`.** "measure" connotes quantification; `infer` (generates *new* information — measurement only extracts) and `select` (the choice-act) fall OUT of it. The invariant's own words — *"reduce to a decidable signal"* — literally describe a decision. RECOMMENDATION: rename to `decide`; keep "measure" only as a public alias IF the measurement-as-evidence / no-self-attestation framing is brand-load-bearing. **This rename is mike's call** (it touches the whole framing) — a decision-log entry, not a silent change.

**Promotion status: QUALIFIED-READY.** CMS earns promotion as *"the discipline for governed/decision-bearing operations"* (NOT "every operation is CMS"). The AGENTS.md line + the portable `uacp.md` MUST carry the governed-scope qualification, or they overclaim.

## The naming sub-question

While testing, challenge step 2's name: do all of `compare / validate / infer / rank / select` sit comfortably under **"measure"**? If yes, the name holds. If one resists, the primitive may need a broader verb (the property is *"reduce to a decidable signal"*, not *"quantify"*).

## Self-reference (the proof is the method)

We validate this axiom **the way the axiom prescribes**: *comprehend* the claim → *measure* it against adversarial cases → *serialize* the verdict. The [verification method](../verification-method/00-the-primitive.md) is the instrument judging its own foundation — if it cannot, that is itself a finding.

## The promotion gate

Only when this matrix is full and counterexample-free does CMS earn promotion to a canonical principle (a neutral line in AGENTS.md + the per-phase mapping in `docs/`) — via a governed run, not an assertion. Until then it is a **named hypothesis**.

## To expand
- Fill the matrix (one row per session; cite the reasoning, not just a verdict).
- Add domains that *stress* it most (anything with no obvious "measure" — e.g. a pure cache write, a heartbeat).
- Record the strongest near-counterexample found, as the honest boundary.
