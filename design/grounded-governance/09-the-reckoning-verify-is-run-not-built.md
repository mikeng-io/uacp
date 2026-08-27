---
type: design
title: "The reckoning (corrected): a sequencing failure, not a paradigm — one grounded screening, executed under a trusted receipt"
description: "The honest conclusion of this bundle's build, corrected by two cross-provider adversarial reviews (Kimi + Codex) that both refuted the first framing. Parking PR #172 is right (~80-85%). But 'non-convergence proves gates don't verify' is overclaimed (~35-40% supported): 6->4->8 findings over a 7k-line diff with a moving source AND a moving reviewer is underdetermined, the gates never claimed to FIND bugs (they enforce that an external screening occurred), and the redirect keeps a turnstile gate — so it is the same architecture shrunk to one instance, not a paradigm shift. The real failure was breadth-before-depth: six per-phase instances built before one converged, plus 1,200 lines of unverified machinery in the trust path, plus fix-forward churn with no scope freeze. The corrected design: one generic screening mechanism with phase-specific substrate producers, a small turnstile that trusts nothing caller-supplied, an INDEPENDENT EXECUTION RECEIPT (host-captured proof of who/what actually screened — without it the loop is verify-theater with better metadata), independence in the pass condition, a findings-corpus that amortizes the semantic tax into deterministic checks, full-substrate re-screen after every fix, and explicit terminal states clean|blocked|escalated. Convergence is a heuristic stop-rule, not a mathematical fixpoint."
tags: [grounded-governance, reckoning, verify, screening, convergence, fixpoint, execution-receipt, sequencing, over-engineering, cross-provider-review]
timestamp: "2026-08-27"
edges: [{dst: 04-grounding-is-per-phase, rel: extends, provenance: asserted}]
---
# The reckoning, corrected by cross-provider review

> This node was first written (2026-08-25) with the headline **"verify is RUN, not built — gates don't verify."** Two independent adversarial reviews from different model families (Kimi, GPT/Codex) — commissioned precisely because same-model review self-attests — **both refuted that headline** while agreeing the parking decision was right. What follows is the corrected conclusion. The original overclaim is preserved in the record below, because a bundle about grounding verification should show its own conclusion being externally witnessed and corrected — that is the loop working on itself.

## The corrected verdict

- **Parking PR #172 is right** (~80-85%, both reviewers). Round 3 was still finding *new* real defects — including a glob `../` traversal (a security hole in a governance gate) and a `cannot_verify` path that could silently finalize. Merging a non-converged, 7,082-insertion / 68-file gate machine into the governance kernel would put unverified code in the exact path trusted to verify. Disqualifying.
- **"Non-convergence proves gates don't verify" is wrong** (~35-40% supported; the rest is rationalization). Three things kill it:
  1. **Underdetermined.** Let `Fₙ` = defects found in source state `Sₙ` by reviewer `Rₙ`. Between rounds *both* `S` and `R` changed (fixes moved the code; a later review surfaced a different class). 6→4→8 over that much surface is non-monotonic by construction — it does not discriminate "gates are the wrong architecture" from the mundane "breadth added before one instance converged, with fix-forward churn and no scope freeze."
  2. **The gates never claimed to find bugs.** `validate_correctness_screening` and its siblings are mechanical turnstiles (artifact-exists / hash-covers / findings-dispositioned). The semantic read was the external reviewer's job *by design*. "The gate didn't catch the bug" is not an objection to what the gate was for.
  3. **The redirect self-refutes.** It keeps "a small gate to make the screening non-skippable." That is a gate. The paradigm did not change — the **size** did, and the **sequencing** did.

**The true failure is sequencing and size, not category.** The `04` generalization ("one machine, six substrates") tripled the machinery — VERIFY + TRIAGE + PROPOSE validators, each with its own kind, severity resolver, substrate hash, screening-docs resolver, and findings-disposition validator (~30 new functions, +1,205 lines in `projection.py` alone) — **before a single instance had converged**, and then fixes landed inside live review rounds, moving the substrate and spawning siblings. Converge one instance before instantiating six.

## The hole both the original and the first review missed

Codex found the requirement that separates a *grounded* verify from theater. The turnstile, even shrunk to one instance, trusts caller-supplied fields — `screener_id`, `verdict`, and the reality-run transcript. **An agent-pasted transcript is just another declaration.** The turnstile can prove a screening *occurred over the current bytes*; it cannot prove the screening was *competent* or that it *actually ran* under the claimed model and lenses.

> Without an independent execution authority, the redirect recreates verify-theater with better metadata.

So the screening's own provenance must be grounded: an **execution receipt captured at a trusted runtime boundary** — which runtime, which model/provider, which lens version, which tools actually ran, and a reality-run transcript that is host-captured, not agent-supplied. This is the piece that makes "RUN a screening" more than a prompt convention. The first reckoning missed it; it is now the load-bearing requirement.

## The corrected design

One generic mechanism, phase-specific substrate producers — **not** the per-phase validator swarm, and **not** Kimi's over-collapse into one vague contract (TRIAGE and VERIFY do not share a substrate; flattening them invents a different failure).

1. **`SubstrateProducer` (per phase, registry-dispatched)** — emits an immutable `{run_id, phase, snapshot_id, evidence_refs, substrate_hash}`. Reality-run evidence must be host-captured/authenticated, never agent-pasted. *(Keep: `gitio.diff_content`, content-addressed binding, the project-slice / code-plane producers.)*
2. **`ScreeningRunner`** — invokes the external, cross-provider screener against the exact substrate under a **versioned lens bundle**; owns the loop, not the kernel. *(Keep: the lenses in `grounding-screening.md` — the best artifact on the branch.)*
3. **`ScreeningArtifact` (governed, immutable)** — `{run_id, phase, substrate_hash, lens_version, execution_receipt, verdict, findings[], parent_screening_id}`. The **execution_receipt** is what the turnstile authorizes against; a free-form `screener_id` is insufficient.
4. **`FindingLedger`** — findings immutable; each fixed, rejected-with-rationale, or escalated. **Confirmed findings become deterministic regression checks where expressible** — the only mechanism that amortizes the semantic tax into a deterministic floor over time (the fuzzing "persist the corpus" import).
5. **`FixpointTurnstile` (the one gate)** — blocks unless, all mechanically: current `substrate_hash` == screened hash; run/phase binding valid; **execution receipt authorized** (trusted runtime, not caller JSON); schema + lens-coverage valid; `verdict == clean`; no finding unresolved; the clean round's screener ≠ the screener whose findings were fixed (**independence in the pass condition**); `cannot_verify` cannot finalize (fail-closed); round/time cap not exceeded.
6. **Explicit terminal states: `clean | blocked | escalated`.** Never "cap reached → pass," never "probably clean." Cap or screener-disagreement → **escalate to a human** (the M3d rework breaker already exists). Two screeners disagreeing is a *finding to adjudicate*, never majority-voted away.
7. **Full-substrate re-screen after any fix.** A fix moves the hash and invalidates the prior clean result; delta screening may *supplement* but never *replace* the whole-substrate clean round. Scope-freeze during a round; batch findings; no intra-round fix-forward (that is what let siblings slip).

**Convergence is a heuristic stop-rule, not a mathematical fixpoint** — call it that. CI retry-until-green is the direct counterexample: a flaky oracle eventually manufactures a clean run. Type-checkers/fuzzing/property-testing get convergence only because their oracle is deterministic; UACP's screening oracle is semantic, so it borrows the loop shape but not the guarantee. Determinism legitimately lives in: hashing, artifact/schema validation, receipt authorization, state transitions, disposition status, caps, screener-identity inequality. Semantic judgment lives in: the read, the lenses, the verdict, the adjudication.

## Keep / delete / change

- **Keep:** substrate producers, content-addressed binding, the lens bundle, typed immutable screening artifacts, immutable findings + resolving remediation references, the config-gated severity ladder (applied *after* dogfood convergence, not before).
- **Delete:** the per-phase validator triplication — duplicated kinds, severity resolvers, substrate hashers, screening-docs resolvers, disposition validators across TRIAGE/PROPOSE/VERIFY.
- **Change vs. the first reckoning:** it is not "gates vs. run-loop." It is **one small turnstile + a trusted execution receipt + an independent, cross-provider screening + a findings-corpus**, built for **one phase to a clean whole-substrate round before generalizing**. The phase-specific grounding *requirement* stays; only the duplicated machinery goes.

## Provenance of this correction

Reconciled from `kimi-reckoning-review.txt` and `codex-reckoning-review.txt` (committed alongside this node) — two cross-provider adversarial audits of this node's original claim. Both independently rated the parking right and the "gates don't verify" framing as overclaimed; Codex additionally surfaced the execution-receipt requirement. The agreement of two different model families on the refutation is the reason to trust it over the single-author original.
