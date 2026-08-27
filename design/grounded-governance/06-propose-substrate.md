---
type: design
title: "PROPOSE grounding: the premise against the real current state"
description: "PROPOSE declares intent, constraints, and a premise — an account of the current state that motivates the work. The disease is asserting that premise without grounding it; a false premise sends the whole run chasing a phantom. The substrate is the reproduced current behavior of the code the premise claims about: reproduce, don't read."
tags: [grounded-governance, propose, premise, behavior-plane, reproduce]
timestamp: "2026-08-24"
edges: [{dst: 04-grounding-is-per-phase, rel: depends_on, provenance: derived}]
---
# PROPOSE grounding: the premise against the real current state

## The declaration and the disease

PROPOSE declares intent, authority, constraints, evidence obligations — and, load-bearing under all of
them, a **premise**: the account of the *current* state that justifies the work. "`toll_fee` eager-loads
the whole schedule on every request." "There is no idempotency guard on the payment webhook." "The
retry path double-counts." The proposal is only as sound as its premise, and the disease is that the
premise is **asserted, never reproduced**. If `toll_fee` does *not* eager-load, if the guard already
exists, if the double-count was fixed last month — the run is chasing a phantom, and no downstream
gate catches it, because PLAN/EXECUTE/VERIFY all inherit the premise as given.

## The substrate: the reproduced current behavior

The reality for a premise is not the code's *text* — it is what the code **actually does now**. So the
substrate is the **reproduced current behavior** of the referent the premise names, produced by the
kernel via `behavior_plane` (the contained-execution primitive already used for VERIFY probes):

- for a **behavioral** premise ("X does Y"), run X against the input the premise implies and capture
  what it actually does — the same "reproduce, don't read" bar VERIFY holds;
- for a **presence/absence** premise ("there is no handler for Z"), a witnessed search of the real
  tree / code plane that Z is in fact absent (or present);
- for a **structural** premise ("this is duplicated across N sites"), the code plane's real count.

The substrate producer here is thin because the primitive exists: it is `behavior_plane` + the code
plane, keyed off the *premise's factual claims* rather than off a diff. What is new is extracting the
premise's checkable claims from the proposal so the kernel knows what to reproduce.

## Mechanism: a screening that must reproduce, not read

PROPOSE grounding is **semantic** (a premise is prose that must be interpreted into a checkable claim)
but its verdict is **grounded in reproduction**: an unexecuted reading of the premise cannot clear it.
The screening, charged like `02`:

- lifts the premise's factual claims into things that can be run/searched;
- reproduces each against the kernel-produced behavior/tree substrate;
- returns typed findings — a premise claim that **does not reproduce** is a P1 finding (the run is
  mis-motivated), and an *un-reproducible* claim (needs an environment the scratch can't stand up)
  returns `cannot_verify`, never a silent pass.

This is the exact `02` discipline pointed at the premise instead of a diff: reproduce, don't read;
ground every verdict; abstain honestly.

## The gate

PROPOSE-exit cannot pass unless every checkable premise claim **reproduced** (or its non-reproduction
was dispositioned — a proposal may legitimately say "I could not reproduce X in the sandbox, here is
the residual risk", which is an *adjudication*, M3d). A premise that fails to reproduce and is neither
fixed (the proposal re-premised) nor adjudicated **blocks**. Fixpoint + config migration as
everywhere: re-premising changes the substrate, invalidating a stale screening.

## Why this is the second-highest leverage

TRIAGE stops a mis-scoped run; PROPOSE stops a **correctly-scoped run built on a false factual
premise** — the failure that looks most like real work (right area, right ceremony) and is hardest to
catch downstream, because every later phase treats the premise as settled. Grounding it turns "the
proposal says X is broken" into "X was run and is in fact broken" — the difference between governance
that processes claims and governance that processes reality.
