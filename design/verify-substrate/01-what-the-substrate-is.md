---
type: design
title: "What the substrate is, and how it is produced"
description: "The substrate defined — the real diff from the true commit range, the reality-run's actual output, the real code/state — and the rule that it must be kernel-produced/witnessed, never agent-supplied. The deterministic floor's job is to make the substrate exist and be grounded, not to judge it."
tags: [verify, substrate, diff, behavior-plane, witness, floor]
timestamp: "2026-08-24"
edges: [{dst: 00-the-substrate-principle, rel: depends_on, provenance: derived}]
---
# What the substrate is, and how it is produced

## The substrate = the real work, made inspectable

Three materials, in order of load-bearing:

1. **The diff from the TRUE commit range** — the actual change set of the run, produced by the kernel
   from the run's real base..head, *not* an agent-nominated path. This is the primary substrate: it
   is what changed, in full, unmediated by the author's account of it.
2. **The reality-run's OUTPUT** — the code actually executed (via `behavior_plane`) and what it did:
   exit status, stdout, observable behavior. Running the work turns *behavior* into material a
   screening can precipitate against ("does this `open()` follow a symlink" is answered by pointing a
   symlink at it and running, not by reading).
3. **The real code, artifacts, and state** — the files as they are on disk, the run's actual
   artifacts, the git-observed reality — not the declaration *about* them.

Contrast with what UACP's verify consumes today (all declaration, no substrate): artifact *presence*,
schema *conformance*, cluster *states*, and *replay of the agent's own authored checks*. None of it is
the work; all of it is the run's account of itself. That is why there is nothing to screen.

## The grounding rule: the substrate is witnessed, never agent-supplied

A substrate the author nominates is the declaration wearing a new coat. So:

- The diff is computed by the **kernel** from the real commit range. Not `bind.command` the agent
  wrote; not a path the agent points at. (UACP already has the git witness in `scope_conformance`;
  today it is only compared to declared `write_paths` and only *advisory*.)
- The reality-run executes the **actual component**, and its verdict is **derived** from the run, not
  reported by the doer. (This is Trustless's Gate 0 posture: `SKIP` must never masquerade as `PASS`;
  the agent cannot set the result.)
- Because the substrate is witnessed, the screening over it is trustable *without trusting the
  author* — which is the whole point of the conformance loop.

## The deterministic floor's job: PRODUCE the substrate, do not judge it

This resolves what the floor is *for*. The floor (the grounded-conformance moves — M2, M3, the
promotions) is **not** the review and is **not** a reviewer role. Its job is to **make the substrate
exist and be grounded** so there is something to screen:

- **M2 (evidence-reference type)** — a claimed fix must *resolve* (run-bound + exists), not merely be
  named. Substrate for the conformance screening: "does the artifact the run points to as proof
  actually exist?" — a real fact, not the agent's word.
- **M3 (behavioral floor)** — when the *witnessed* diff shows code changed, force a behavioral check
  to be authored and **run**, so its output becomes substrate. The floor does not classify the work by
  keyword-guessing (a pre-digest); it keys off the **fact** that the diff touched code, and makes the
  reality-run produce material.
- **Promote the git witness** (`SC_DIFF_*` warn→block, with a migration) — make the one independent,
  witnessed input actually bind, so containment is a fact the screening can rely on.

The floor is the machinery that guarantees a real, grounded substrate is present at VERIFY. It does
not decide whether the work is *correct* — that is the screening's job (`02`).

## The anti-pattern this rules out

`witness_class` / keyword classification (`"behavior"`, `"wire"` → a class label) is the wrong instinct
precisely because it **pre-digests the substrate into a label** and then grades against it — a
structural proxy for a behavioral property, exactly what a screening is supposed to render
unnecessary by looking at the real thing. Facts (the diff touched code; the run exited non-zero) belong
to the floor; *judgment* (is this behavior correct?) belongs to the screening agent, over the
substrate.
