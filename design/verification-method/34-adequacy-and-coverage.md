---
type: design
title: Adequacy & Coverage — who verifies the verifier-generation (3 layers)
description: >-
  The anti-gaming model: because the agent AUTHORS the checks, the checks themselves must be governed.
  Three layers, determinism-first. (1) STRUCTURAL coverage — every target must be measured_by >=1 check,
  reusing the coverage gate built this session (closes #503 class D for checks, fail-closed). (2) The
  required-kinds FLOOR — a policy mapping target classes to mandatory check-kinds, so a weak-but-present
  check (class B) cannot satisfy a target whose class demands a stronger kind. (3) COUNCIL default-to-refute
  on the residual semantic adequacy. Layers 1-2 are deterministic gates; layer 3 is the only judgment.
tags: [verification, generative-gate, adequacy, coverage, anti-gaming, required-kinds, council]
timestamp: 2026-06-25
edges:
  - {dst: 31-replay-engine, rel: depends_on, provenance: derived}
  - {dst: 15-coverage-serialization, rel: extends, provenance: derived}
  - {dst: 14-council-method, rel: depends_on, provenance: derived}
---

# Adequacy & Coverage — who verifies the verifier-generation

The generator ([33](33-generator-synthesis.md)) is a *semantic* step, so it cannot be trusted alone — a
lazy or adversarial agent could author **weak** checks (always-true — #503 class B) or **omit** checks
for some targets (class D, recursively). This node is the governance over the generation. Three layers.

> **Honest framing (council correction, 2026-06-25 — unanimous cross-provider + subagent).** Determinism
> here does **less** than "determinism-first / can't be gamed" would imply. Layers 1-2 deterministically
> force **omission** (D) and **gross wrong-kind *given an honest class*** (B-coarse). They do **not** force
> an **honest classification** — and the floor (Layer 2) keys off the agent's *declared* class. So the
> residual the council (Layer 3) owns is **classification honesty + subtle weakness**, and that residual is
> larger than a "3 deterministic layers" reading suggests. The accurate claim: *determinism NARROWS the
> council's surface to classification-honesty; it does not eliminate it.* The mitigation in Layer 2b below
> shrinks that surface further by grounding the class in content; it does not fully close it (only the code
> plane, which entails the class from the real symbol kind, does — and that is later).

## Layer 1 — STRUCTURAL coverage (deterministic; reuses what we built)

**Every target must be `measured_by` ≥1 check.** This is *exactly* the coverage gate shipped this
session ([15](15-coverage-serialization.md)), applied to a new edge: where the dropped-intent gate proved
"every `scope_item` is `derives_from` a `work_unit`," the check-coverage gate proves "every
`scope_item`/`work_unit` is `measured_by` a `check`." Same machinery — projection enumerates targets +
`measured_by` edges; a target with no inbound `measured_by` is `GP_UNCHECKED_TARGET` (block), phase-keyed
at the relevant exit and forced on the live path. Closes class D for checks, fail-closed, with no new
gate architecture — just a new check function in `projection.py` and a new edge the binder emits.

This composes with the replay engine ([31](31-replay-engine.md)): coverage proves checks *exist*; replay
proves the checks that exist *pass*. Neither alone is sufficient; together they are "every target is
proven, and the proof runs."

## Layer 2 — the required-kinds FLOOR (deterministic policy)

Coverage stops omission but not *weakness*: a `field_present` check on a "wire up the /settle route"
work_unit is present-but-useless. The floor closes that deterministically: a **policy table maps the
target's class → the minimum check-kind(s) it must carry.**

```yaml
# config: verification-floor.yaml  (doctrine -> stays YAML; the engine reads it)
target_class_floor:
  wires_symbol:    [uacp.check.symbol_resolves]      # a "wire/mount/register X" intent
  sets_value:      [uacp.check.field_equals]
  ensures_obligation: [uacp.check.obligation_satisfied]
  changes_behavior:   [uacp.check.behavioral]        # (code/behavior plane — blocks until wired, by design)
```

The target's class is the generator's recorded comprehension (`from.basis` / an explicit `class` field).
A `wires_symbol` target whose only check is `field_present` fails the floor (`CHK_FLOOR_UNMET`, block).
The floor is what makes "a 'wires up X' claim needs a *resolution* check, not 'a file exists'" an
enforced rule, not advice. (Honest edge: a `changes_behavior` floor requires a behavioral/code check,
which BLOCKS until that plane is wired — [32](32-reality-binder.md) — correctly refusing to let such work
close on a weak proxy in the meantime.)

### Layer 2b — class ENTAILMENT cross-check (deterministic, partial)

The loophole all three reviewers led with: the floor keys off an **agent-declared** class, so an agent can
mis-classify a `wires_symbol` work_unit as `sets_value`, satisfy the floor with a weak `field_equals`, and
pass Layers 1-2 green. Layer 2b shrinks that surface deterministically (it cannot fully close it):

- **Content cross-check.** Derive a *candidate* class from the target's OWN serialized content — the
  `work_unit.intent` / `expected_outputs` text (a fixed keyword/pattern map: `wire|mount|register|route`
  → `wires_symbol`; `set|update|configure` → `sets_value`; …). If the declared class is *weaker* than the
  candidate the content implies, emit `CHK_CLASS_UNDERCLAIM` (block / council-priority). This forces the
  agent to mis-state the **intent text too** — which the council reads and other gates already consume —
  not just a private label.
- **Serialize the entailment, not just the class.** The check records `from.class` AND the basis it was
  derived from, so an auditor can see *whether the class follows from the content*, not just assert it.
- **The code plane closes it fully (later).** Once the `code` plane lands ([32](32-reality-binder.md)), a
  `wires_symbol` claim's check binds to the real symbol kind — the class is then *entailed by reality*, not
  declared. Until then, 2b is a heuristic floor and Layer 3 owns the residual.

Honest residual: 2b raises the cost of gaming (mis-classification must now also corrupt the intent text and
survive the council); it does not make classification-honesty deterministic. Only the code/behavioral plane
does — the bundle does not claim otherwise.

## Layer 3 — COUNCIL default-to-refute (the only judgment)

What determinism cannot decide — *is this `field_equals` actually proving the intent, or a plausible
dodge? is the target's class honest?* — is the council's job, in its narrowed
[default-to-refute](14-council-method.md) posture: each generated check is a claim a verifier must try to
REFUTE ("this check does not prove its target"); a check survives only if the panel fails to refute it.
The verdict serializes to the [investigation ledger](13-investigation-ledger.md). Layer 3 runs over the
*residual* — the checks Layers 1-2 admitted — so the panel spends judgment only where it is irreducible.

## The division of labor (why three layers, not one)

- **Omission** (class D) → Layer 1, deterministic.
- **Wrong *kind*** (class B, gross) → Layer 2, deterministic.
- **Subtle weakness / dishonest class** (class B, fine) → Layer 3, judgment.

Each failure mode handled at the cheapest layer that can decide it; the council is reserved for the
genuinely semantic residual — the same "determinism where possible, judgment only for the rest" split as
the rest of UACP.

## What is built vs new

- **Built / IMPROVISE:** the coverage-gate machinery (`projection.py` self-gating checks + the
  phase-keyed/forced wiring — proven this session); the council default-to-refute posture
  ([14](14-council-method.md)); the doctrine-YAML config pattern.
- **New (BUILD):** Layer 1 = the `measured_by` check + `GP_UNCHECKED_TARGET` (slice 0/2); Layer 2 = the
  floor table + its engine (slice 2); Layer 3 = the council hook that enumerates checks as refute-targets
  (slice 2, extends [14](14-council-method.md)).

## To build

- Slice 0/2: `_check_unchecked_target` in projection + the `measured_by` edge from check nodes.
- Slice 2: `verification-floor.yaml` + the floor engine; the council enumeration of checks-as-claims.
- Tests: a target with no check blocks (L1); a `wires_symbol` target with only `field_present` blocks
  (L2); each non-vacuous (the teeth fail before the rule).
