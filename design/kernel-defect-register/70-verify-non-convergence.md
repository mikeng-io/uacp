---
type: decision
title: The verdict — building gates did not converge, and cannot
description: Why the remediation lane was parked. Three rounds of external review on the grounding PR found new real defects each time; the last two show structurally why a declarative gate cannot reach them.
tags: [verify, convergence, verdict, semantic-verification]
timestamp: 2026-08-27
edges:
  - {dst: 60-remediation, rel: supersedes, provenance: asserted}
  - {dst: 20-grounding-defects, rel: extends, provenance: asserted}
---

# The verdict

This node supersedes the standing of `60-remediation.md`. The register's findings hold; the
*approach* to fixing them did not.

## What happened

PR #172 (`feat/verify-grounding`) built grounding gates — the conformance floor M1–M5 plus
per-phase grounding. It went through three rounds of external review. Each round found **new,
real defects the gates had missed**, in different classes each time: 6, then 4, then 8, then 2
more on `545e3886` (2026-08-26).

**Non-convergence is the verdict.** A review loop that never runs dry is not a loop converging
slowly; it is evidence that the mechanism under construction does not address the class.

## The two findings that show why

Both verified directly in the code on `origin/feat/verify-grounding`, and both land on the
`next`-response block — the M4 emission fix. So the fix for the emission gap introduced a
data-loss bug and a null-out bug, and verify passed both.

> **Evidence is transcribed below rather than cited to a branch.** Both findings live on
> PR #172 at commit `545e3886840861a6848e5e1e9c62b7b82e8ffc7b` (`feat/verify-grounding`).
> A branch ref is mutable and an unmerged commit is not reachable from a fresh clone, so the
> decisive lines are quoted verbatim here — a calibration set that cannot be reproduced is
> prose, not a calibration set.

### P1 — the author's blind spot, by construction

`RunManifest` has no `deferred_items` field. Every field it declares:

```python
class RunManifest(BaseModel):
    run_id: str
    status: Status = Status.active
    current_phase: str = "triage"
    created_at: str = Field(default_factory=lambda: _iso_now())
    authority: Authority
    workspace: Workspace = Field(default_factory=Workspace)
    artifacts: dict[str, str] = Field(default_factory=dict)
    state_history: list[StateHistoryEntry] = Field(default_factory=list)
    finalized_at: str | None = None
    abort: AbortRecord | None = None
    track: str = "standard"
    goal_id: str | None = None
    inherits_from: str | None = None
    # + reworks / rework_depth / carried_findings / inherited_artifacts
```

The transition path reads the field out of the **raw** manifest instead, and its docstring
records that the author saw the asymmetry:

```python
    """Replay the obligations a prior phase deferred forward: the run manifest's
    ``deferred_items`` ... Read from the RAW manifest (the state-machine
    ``RunManifest`` model does not model deferred_items)."""
    ...
    items = raw.get("deferred_items")
```

They compensated on the **read** side. `_save_manifest` serializes `RunManifest`, so the
**write** side strips the field: the mechanism built to replay carried obligations deletes
those obligations on the first transition after they are recorded.

This is the decisive case, and the reason needs stating precisely — the loose version of it is
refuted by this bundle's own D-07.

**Not** *"every UACP gate consumes the author's declaration"*: `scope_conformance` reads the real
git change set, and the register calls that an independent witness. The accurate claims are
narrower, and all three hold:

1. **Every *blocking* gate consumes a declaration.** The one independently-witnessed input is
   `SC_DIFF_*`, `warn` at both sites (D-07). Nothing that can refuse a transition reads reality.
2. **The witness that exists could not have seen this defect anyway.** `SC_DIFF` asks *"did the
   change set stay inside the declared write paths?"* — P1 is a data-loss bug *inside* a declared
   path. A containment witness is the right shape for scope drift and the wrong shape for
   correctness; promoting it to `block` would not have caught P1.
3. **The generative gate asks the author to author the checks**, so it reaches only what the
   author already suspects. The docstring above proves this author was thinking hard about
   exactly this field — and nobody writes *"transition twice, confirm the field survives the
   round-trip"* unless they already suspect the round-trip is lossy.

So the defect was unreachable by construction, not by oversight. Note that (2) is the
load-bearing half: it is not enough to *have* a witness — the witness has to be pointed at the
right question.

### P2 — declaration and reality diverging inside one function

`_state_policy()`'s docstring promises an overlay; the body assigns over it:

```python
    # docstring: "... then overlaid by the workspace's own config/state.yaml when
    #             present (a project override wins)."
    out: dict[str, Any] = {}
    candidates = [<install-relative config/state.yaml>, workspace / "config" / "state.yaml"]
    for path in candidates:
        ...
            if isinstance(raw, dict):
                out = raw  # later (workspace) candidate wins as an override
```

`out = raw` is replace, not overlay. A partial workspace `config/state.yaml` therefore drops
`lifecycle_skill_contracts`, and every `next.required_skill` / `next.write_scope` becomes null.

A conformance gate reads the declaration. Here the declaration and the reality disagree **inside
a single function**, and only something reading the code catches it.

## The structural claim

> A declarative check covers only the anticipated. The unanticipated requires an adversarial
> reader on the real work.

More gates enlarge the *declared* surface — more kinds, more resolvers, more edge cases to get
right — without enlarging what is *verified*. That is why rounds produced new defect classes
rather than a shrinking tail: each round of gate-building added surface that the next round
found defects in.

Verification is a **semantic act**: run an adversarial screening against the real diff and
iterate on the fix delta until a round comes back clean — the fixpoint. It is not a gate
check.

## What this changes in this bundle

- **The register (`00`–`40`) stands.** Those 18 defects were found by reading the kernel, and
  the two above are the same method producing more. Nothing here is retracted.
- **`60-remediation.md` is re-scoped, not deleted.** M2 (the evidence-reference type) and M4
  (the response envelope) are corrections to specific broken mechanisms and remain valid on
  their own terms. **M3 — "ground the planes that already exist" — is gate-building and is
  parked** with the lane.
- **D-03 now has an owner** — it had none (`60-remediation.md` M6). Its Guardian-coverage half
  is gate-building and parks with the lane; its coherence half — a per-phase dispatch rule that
  reads as policy and is inert — is a cheap standalone fix and does not park.
- **M0 still stands and matters more than before.** UACP is developed in an environment where
  UACP is inert (D-14). Whatever replaces the gate lane has to be felt during development or it
  will repeat this.

## Calibration set

P1 and P2 are the right acceptance test for whatever replaces the gates, precisely because both
were found by a reader with **less** context than UACP had: git-diff only, no run state, no
manifest, no ledger. The question to ask of any successor mechanism is not "does it pass its own
checks" but *"would it have found the `deferred_items` round-trip and the `out = raw` replace?"*

Planted-fault calibration against these two is the honest first gate on the next design.
