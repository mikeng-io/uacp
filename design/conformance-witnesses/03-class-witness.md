---
type: decision
title: "Class witness — per-target symbol claim, kernel-mapped connectivity heuristic (witness #2)"
description: "Extends the scope-witness seam to the Verification-strength layer (issue #87): a scope_item/work_unit optionally claims its code symbol; the gate reuses the gate-invoked codeflair derivation for per-symbol connectivity FACTS; the kernel maps facts to an entailed class via the LOCKED heuristic and feeds validate_class_underclaim. The agent-writable entailed_class manifest field is superseded wherever the witness is active."
tags: [conformance, witness, class-underclaim, codeflair, decision, verification]
timestamp: 2026-07-03
edges:
  - {dst: 02-scope-witness-seam, rel: extends, provenance: asserted}
---
# 03 — The class witness (witness #2)

## What converts

`validate_class_underclaim` (`engines/manifest/projection.py:998`) grades the
strongest class a target's checks DECLARE against an oracle class. The oracle
slot exists in code and is explicitly independence-shaped ("independent
oracle", strongest-wins vs the legacy prose match) — but the value it reads,
`entailed_class`, is projected off the agent's own manifest
(`scope.in_scope[].entailed_class`, `work_units[].entailed_class` —
`projection.py:155,177`). The oracle is agent-forgeable: the row is
**self-attested** on the scoreboard. Issue #87 converts it by feeding the
slot from the code plane.

## Decision

**Reuse the 02 seam wholesale** — same trust root, same doctrine, one new
facts surface:

- **Claim (per-target)**: a `scope_item` / `work_unit` may declare
  `code_ref: {file, name}` — the same ref format as the scope artifact's
  `code_refs` (store `file` column path + class-qualified name). This is the
  falsifiable binding Shim-B lacked (Shim-B governed `code_anchor` INSIDE the
  kernel — wrong seam; here the kernel only carries the claim and compares).
  Absent `code_ref` → the class witness no-ops for that target while
  advisory, and the legacy oracle path (agent `entailed_class` / prose)
  continues unchanged — strictly additive.
- **Derivation (facts only)**: the gate execs the SAME configured codeflair
  CLI (02's kernel-default trust root, argv screening, 120s/retry/memo
  envelope, env scrub, fresh store) with a new facts surface for the claimed
  symbols — per symbol: resolution fact, inbound reference count (hop-1
  fan-in, the spike-validated signal), hop-1 edge list with reason enum, and
  the wiring facts the heuristic needs. No classes cross the wire — classes
  are verdicts, and the witness reports facts (02's inversion lesson).
- **Mapping (kernel-side, the LOCKED heuristic from #87)**: the kernel maps
  facts → entailed class:
  - **no inbound references** → `sets_value` (nothing consumes it; the
    weakest wiring class);
  - **wired-in** (inbound references exist — something resolves/calls it) →
    `wires_symbol`;
  - **broad blast radius** (hop-1 fan-in at/above a bound derived from the
    spike's separation data, NOT closure magnitude — 02's signal discipline
    holds here verbatim) → `changes_behavior`.
  This is a connectivity heuristic, NOT a per-framework wiring catalog
  (locked in #87); thresholds live in kernel code next to the mapping, cited
  to the spike table.
- **Feed + supersession**: when the witness derives a class for a target,
  `validate_class_underclaim` uses IT as the oracle, and the agent-written
  `entailed_class` for that target is IGNORED with a visible advisory when it
  disagrees (`CHK_ENTAILED_CLASS_SUPERSEDED`, warn) — the forgeable field is
  never silently trusted alongside a live witness. Where the witness is
  absent/unavailable, today's behavior is byte-identical (fail-closed
  `CHK_ENTAILED_CLASS_INVALID` and the prose fallback stay as-is).
- **Dial**: advisory-first exactly as 02 — new codes are `warn`;
  `sets_value`-vs-declared mismatches surface through the existing
  `CHK_CLASS_UNDERCLAIM` machinery only when the witness-derived rank
  exceeds the declared rank (the gate's comparison is unchanged; only the
  oracle's provenance upgrades). Promotion rides 02's criteria — this
  witness adds NO new promotion track; it is the "proving ground more than
  payoff" gate #87 names.

## Why this is the whole design

Everything hard was decided in 02 and survives unchanged: trust root,
facts-only wire, freshness-by-construction, envelope, availability doctrine,
signal discipline (hop-1 only). The only new decisions here are (a) the
per-target claim field, (b) the facts surface for single symbols, and (c) the
supersession rule for the legacy field — each stated above. The build is
scoped to: schema (`code_ref` on scope_item/work_unit write-time shapes),
projection carry, one codeflair facts extension, the kernel mapping fn +
threshold, the oracle feed in `validate_class_underclaim`, teeth tests per
heuristic branch, and an e2e proof reusing the 02 harness.

## Status / Checkpoint

> **2026-07-03 — DESIGN.** Node authored from the E1 recon (as-built oracle
> slot + projection carry points confirmed by LSP); awaiting review round.
