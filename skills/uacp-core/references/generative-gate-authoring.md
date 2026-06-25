---
type: contract
title: Generative-Gate Authoring
description: The producer contract — how PROPOSE/PLAN/VERIFY author the frozen uacp.check.* checks that prove their targets (comprehend→author→serialize), so the kernel can re-run and gate them.
tags: [verification, generative-gate, authoring, checks, comprehend-measure-serialize]
timestamp: 2026-06-25
---

# Generative-Gate Authoring — the producer contract

The verification gate only has teeth if each phase **authors a specific, runnable check per
target it owns**, the kernel **freezes** it, **re-runs** it, and **blocks "done"** if any check
is missing, weak, or failing. This is the *one* place a semantic act happens: you read what the
work actually claims and SELECT + PARAMETERIZE a check from the closed catalog. Everything
downstream is deterministic — you author the check, you never hand-write a verdict.

Generation is **bounded to selection from the closed catalog** (never free-form code), and it is
**not trusted alone**: the kernel disposes (coverage, the required-kinds floor, class entailment,
and frozen replay), and the council refutes the residual. You propose; the kernel + council dispose.

## The three steps (a governed-writer step, not a habit)

For each target the phase owns:

1. **comprehend** — read the target's intent + expected outputs and CLASSIFY it: does it *wire* a
   symbol, *set* a value, *ensure* an obligation, or *change* a behavior? Record the class as
   `from.class` and the text you derived it from as `from.basis`. The class vocabulary and the
   class→required-kind floor are AUTHORITATIVE in `UACP_ROOT/config/verification-floor.yaml` (do
   not restate the table from memory — read it; the engine reads the same file).
2. **author** — `uacp_entity_write` ONE `uacp.check.<kind>` per target, choosing the kind(s) the
   class *requires* (the floor) plus any you judge necessary, parameterized from the content:
   - `from.target` = the target's node id (this is the `measured_by` edge the coverage gate reads);
   - `from.class` = the class you comprehended; `from.basis` = its textual basis;
   - `bind` = what the check evaluates against (an artifact `ref`, a graph triple, or an
     `obligation_id`); `expect.value` for `field_equals`; `severity: block`.
3. **serialize** — the entity-writer validates against the schema, watermarks, and auto-registers
   it, so it projects as a `check` node and the replay engine + coverage gate see it. Same trust
   path as every other manifest entity.

## The closed catalog (SELECT from these — authority: the schema + layout registries)

These are the kinds you can author today (they match `layout.CHECK_KINDS` /
`schema._CHECK_SUBKINDS` — the entity-writer rejects any other kind at validate-on-write):

| kind | proves | binds against |
|---|---|---|
| `uacp.check.field_present` | a field/section is concretely present & non-empty | an artifact `ref` |
| `uacp.check.field_equals` | a field equals an expected value (needs `expect.value`) | an artifact `ref` |
| `uacp.check.edge_exists` | a required coverage/topology edge exists | the projected graph |
| `uacp.check.obligation_satisfied` | an evidence obligation has a passing assessment, no uncleared block | the projected graph |
| `uacp.check.artifact_integrity` | an artifact is unchanged since its watermark | the watermark index |
| `uacp.check.symbol_resolves` | a claimed symbol resolves to ≥1 real SCIP descriptor — the `wires_symbol` floor kind; `bind.ref.symbol` = the name | the Codeflair code index |

**`symbol_resolves` is fail-closed-until-an-index-exists (code plane, slice 3):** it resolves against
the run's Codeflair SCIP index. If that index has not been built for the run it ERRORs (block) — so a
`wires_symbol` target cannot close until the code plane is actually built; it never false-passes on a
textual shadow (the #503 `grep route_mounted` fix).

**Still not authorable (do NOT select):** `uacp.check.behavioral` (the `changes_behavior` floor kind)
is the behavioral plane — a sandboxed runner, deliberately last (node 32). A `changes_behavior` target
therefore has no authorable check that satisfies its floor and correctly **blocks until that plane is
wired**. Do **not** down-classify a target to dodge that — the class-entailment check
(`CHK_CLASS_UNDERCLAIM`) reads your intent text and blocks an underclaim.

## Per-phase synthesis (what each phase authors)

| phase | targets | typically authors | binds against |
|---|---|---|---|
| **PROPOSE** | each `scope_item` (intent) | one `field_present` that the intent is concretely stated; record what PLAN must prove as its `from.basis` (a forward-reference) | the proposal artifact (`ref`) |
| **PLAN** | each `work_unit` | the floor-required kind for its class — `field_equals` (set), `obligation_satisfied` (ensure), `symbol_resolves` (wire — code plane, resolves against the code index); plus `edge_exists` where coverage topology must hold (author-judgment, not floor-required) | artifact / graph / code index |
| **EXECUTE** | — | **nothing** — EXECUTE produces the *evidence* the VERIFY checks bind to; it does not author checks | — |
| **VERIFY** | each obligation / done-claim | `obligation_satisfied` (graph), `artifact_integrity` (watermark), and (later) `behavioral` — the reality-binding pass | graph / watermark (+ later behavior) |

> **PROPOSE and `from.class`:** a PROPOSE `field_present` proves only *"the intent is stated"* — do
> NOT stamp it with a strong `from.class` (e.g. `wires_symbol`). The floor binds the class of the
> WORK at PLAN/VERIFY; a strong class on a PROPOSE presence-check would trip `CHK_FLOOR_UNMET` (its
> floor kind isn't `field_present`). Carry the intent's eventual class as `from.basis` prose (what
> PLAN must prove), not as a floor-triggering `from.class`.

The PROPOSE→PLAN→VERIFY chain is itself a coverage chain: a PROPOSE intent-class basis names what
PLAN must prove; PLAN binds it to a symbol/field; VERIFY binds it to evidence. A break anywhere is
caught by the structural coverage gate (`GP_UNCHECKED_TARGET`).

## What the kernel does with what you authored (so you can't self-attest)

- **coverage** (`GP_UNCHECKED_TARGET`) — every `scope_item`/`work_unit` must be `measured_by` ≥1 check.
- **the floor** (`CHK_FLOOR_UNMET`) — the target's class dictates the minimum kind; a `field_present`
  cannot "prove" a "wire X".
- **class entailment** (`CHK_CLASS_UNDERCLAIM`) — your declared class is cross-checked against the
  target's own intent/expected-outputs text; an underclaim blocks.
- **replay** (`CHK_*` fail/error) — each frozen check is re-run; a fail or unresolvable bind blocks
  (ERROR ≠ PASS).

These run forced at the VERIFY exit and again at closure. Honest limit: the gate proves a check is
present, of the right kind, and not under-claimed; whether its `bind` is genuinely *relevant* to the
target is the council's (and, later, the code plane's) job — author in good faith.
