---
type: analysis
title: Spike — Findings & As-Built Evidence (Slice 1)
description: EVIDENCE, not design contract. Grounded findings from exploring the scope_item migration surface and the real manifest fixtures, plus (below) the closure-report result that self-demonstrates the PROPOSE→PLAN seam.
tags: [graph-engine, spike, evidence, as-built]
timestamp: 2026-06-20
validates: 20-slices-readiness.md   # the design intent this evidence tests
lifecycle_phase: brainstorm         # this spike IS the BRAINSTORM-phase activity (D31)
feeds: [propose.viability, plan.compat-shim]   # the evidence this brainstorm produces
---

# Spike — Findings & As-Built Evidence

> **This is EVIDENCE / as-built, NOT design contract.** It records what is *actually* in the tree today
> and what the spike *proved*. The design (intent) lives in the bundle nodes; this links to it, does not
> redefine it. Every claim cites a real path. (Doc-discipline: separate intent from evidence; link,
> don't inline.)

## Job 1 — the `scope_item` migration surface

**Today's shape:** `scope.in_scope` is `list[string]` — bare prose, no identity. Real example:
`proposals/uacp-governed-lifecycle-dry-run-proposal.yaml:9-14`:
```yaml
scope:
  in_scope:
    - "UACP_ROOT docs/config/state alignment"
    - "Lifecycle skill usage and routing"
    - ...
```

**Migration-break finding (smaller than feared — but FLAGGED for spike verification):** the exploration
grep found **no programmatic reader that structurally depends on the bare-string form** — the closure
checks, scope_item ids, and `derives_from` are all *design-only / not-yet-implemented* (per
`16-schema-registry.md`: "No schema at all for `uacp.proposal`…"). So the projector is greenfield.

> ⚠️ **CORRECTED (2026-06-20) — my first grep was VACUOUS.** This working tree is on a stale porting
> branch (`uacp/runtime-porting-…`) where `skills/` source is absent (`ls skills/…/*.py` → "no matches
> found"). So "0 matches" meant *files missing*, not *no readers*. Re-checked against **main**
> (`git grep in_scope main`): there ARE readers —
> - `scripts/validate_uacp_artifacts.py:438` — `if "in_scope" not in scope: BLOCK` (key **presence**).
> - `skills/uacp-core/scripts/engines/domain/phase_transitions.py:183` — brainstorm-admission requires a
>   **non-empty** `in_scope`.
>
> **Both are presence/non-emptiness checks, not item-structure readers.** So the `scope_item.id` migration
> is **additive-low-risk** (keep the `in_scope` key present + non-empty → both still pass), **but a
> compat-shim IS needed** — the council's Integration F2 **stands** (my "relaxes it" was wrong). **TODO:**
> read the actual brainstorm-admission logic (not just the description string) to confirm it doesn't
> assume string items. **Lesson:** always verify a grep against `git grep main` when the working tree may
> be a partial branch.

## Job 2 — real manifest fixtures (the demo target)

**Best complete run:** `uacp-governed-lifecycle-dry-run` (proposal→plan→execute→verify→resolve present).
All YAML, **one file per artifact** (PIV/plan carry a `work_units:` *list* inside one file).

Files to glob + parse:
```
proposals/uacp-governed-lifecycle-dry-run-proposal.yaml      # kind: uacp.proposal  → scope.in_scope[]
plans/uacp-governed-lifecycle-dry-run-plan.yaml              # kind: uacp.plan      → work_units[].id  (NO derives_from)
executions/uacp-governed-lifecycle-dry-run.yaml              # kind: uacp.execution → work_units[].id/status
verification/uacp-governed-lifecycle-dry-run-verification.yaml
outputs/uacp-governed-lifecycle-dry-run-summary.yaml
state/runs/uacp-governed-lifecycle-dry-run.yaml              # run manifest
```
PIV/assessment edge shapes (from fixtures `.outputs/plans/*-piv.yaml`, `.outputs/verification/*-piv-assessment.yaml`):
- PIV: `work_units[].id`, `evidence_obligations[].id` + `.work_unit_id` (→ `obligation_for`, derived)
- assessment: `piv_contract` (path FK), `assessments[].obligation_id`, `evidence_refs`, `state/result`

**Key gap confirmed in real data:** the plan's `work_units` carry **no `derives_from`**, and the plan
*repeats* the proposal's `in_scope` prose instead of keying back to it — i.e. the PROPOSE→PLAN edge is
absent in the actual fixtures, exactly as the design diagnoses (`01-context-intent.md:31-37`).

## Parsing strategy for the spike

1. Glob the run's files by `kind`. 2. Build `nodes` (id, kind, run_id, path) + `edges`
   (src, dst, rel_type, provenance) in memory. 3. Synthesize ephemeral `scope_item` ids from
   `in_scope[i]` (compat shim). 4. Emit `derives_from` edges only where a plan work_unit carries the key
   (none today → all uncovered). 5. Run closure checks.

## Expected closure result (the prediction)

- **`uncovered`**: every synthesized `scope_item` (no inbound `derives_from`) → dropped intent.
- **`orphan`**: every plan `work_unit` (no `derives_from` to a scope_item).
- **`unverified`**: likely none for this run (execution + verification present).
- → This report *is* the self-demonstration of the broken seam.

## Result — spike run (2026-06-20) ✅ SEAM DEMONSTRATED

`python3 spike/projector.py uacp-governed-lifecycle-dry-run` →
```
nodes: 11  {scope_item: 9, work_unit: 2}    edges: 0
[FAIL] uncovered   9   ← every in_scope intent (proposal 5 + plan 4), none with inbound derives_from
[FAIL] orphan      2   ← plan.package, resolve.package (no derives_from to a scope_item)
[FAIL] unverified  2   ← (legacy run: ad-hoc `checks`, no per-work_unit assessments)
[ok  ] phantom     0
>> PROPOSE→PLAN seam DEMONSTRATED: 9 uncovered intents, 2 orphan work_units, 0 derives_from edges.
```

**What this proves:**
- The in-memory projector (~130 lines, stdlib + PyYAML, read-only) builds the graph and runs closure
  checks against real manifests in milliseconds — **D20 (in-memory vertical) is validated; no DB needed.**
- The closure checks **self-demonstrate the broken seam** on today's data, exactly as the design predicts
  (`14-projection-engine.md` "self-demonstrates"). 0 `derives_from` edges = the missing PROPOSE→PLAN link.
- Real legacy structure observed: the plan **repeats** the proposal's `in_scope` prose (9 distinct
  statements across the two) instead of keying back — the divergence the design fixes; and `work_units`
  live in the **execution**, not the plan (legacy manifests have no clean work_unit layer).

**Caveats / honesty:** `unverified=2` is an artifact of the legacy verification format (run-level
`checks`, not per-work_unit `assessments`) — not a real coverage gap for this dry-run; it shows the
closure check is strict, and that the assessment→work_unit edge is genuinely absent in old data.
`phantom=0` is correct (no edges exist to dangle yet).

## Piece 1 — the FIX proven (new canonical form, 2026-06-20)

Built the new canonical form (clean break, D32) and a sample run `spike/fixtures/oauth-login/`:
- `proposal.yaml`: `scope.in_scope` items are **keyed** — `{id: si-1, statement: ...}` (was bare strings).
- `plan.yaml`: `work_units` carry **`derives_from: [si-1]`** — the missing PROPOSE→PLAN edge.

`python3 spike/projector.py --dir spike/fixtures/oauth-login` →
```
nodes: 5  {scope_item: 2, work_unit: 3}   edges: 3  by-rel={derives_from: 3}
[ok  ] uncovered   0     ← every intent is covered
[ok  ] orphan      0     ← every work_unit is anchored
[FAIL] unverified  3     ← expected (no assessments in this minimal fixture)
[ok  ] phantom     0
>> PROPOSE->PLAN seam CLOSED — intents covered: 0 uncovered, 0 orphan, 3 derives_from edges.
```

**Both directions now proven by the same projector:**

| run | uncovered | orphan | derives_from | seam |
|---|---|---|---|---|
| legacy `uacp-governed-lifecycle-dry-run` | 9 | 2 | 0 | **broken** |
| new-form `oauth-login` | 0 | 0 | 3 | **closed** |

The two keys (`scope_item.id` + `work_unit.derives_from`) fix the seam end-to-end — the *same* read-only
in-memory projector validates both in milliseconds, no DB. **Piece 1 of Slice 1 is proven.** (`unverified=3`
is correct — this minimal fixture has no EXECUTE/VERIFY artifacts yet; adding them is a later piece.)

## Piece 1b — full end-to-end chain COMPLETE (2026-06-20)

Extended `fixtures/oauth-login/` with **`execution.yaml`** (checkpoints) + **`verification.yaml`**
(assessments) and added a **`--trace`** walk. The full chain now exists and is traversable both ways:

```
intent (scope_item) ←derives_from─ work_unit ←─ obligation_for (ev) / checkpoint_of (cp) / work_unit_id (as)
                              assessment ─obligation_id→ ev ,  ─evidence_refs→ cp
```

`projector.py --dir fixtures/oauth-login --trace si-1` →
```
nodes: 14 {scope_item:2, work_unit:3, evidence_obligation:3, checkpoint:3, assessment:3}
edges: 18 {derives_from, obligation_for, work_unit_id, obligation_id, evidence_refs, checkpoint_of}
[ok] uncovered 0  [ok] orphan 0  [ok] unverified 0  [ok] phantom 0
TRACE si-1: all 5 kinds reached → END-TO-END chain COMPLETE (PROPOSE→PLAN→EXECUTE→VERIFY)
```

**Proven end-to-end:** every intent is covered, every task anchored AND verified, every evidence unit
linked, no dangling edges — and the chain walks **both directions** (intent→assessment "did it get done?",
assessment→intent "why does this exist?"). Both the **task** (`work_unit`) and its **unit/evidence**
(`obligation`+`checkpoint`) are linked and verified. The full link-up is demonstrated.

## Piece 1c — edge cases: checks flag PRECISELY + a design refinement (2026-06-20)

Added 3 middle-ground fixtures (the extremes all-broken/all-clean don't test precision):

| case | result | verdict |
|---|---|---|
| `partial/` (si-2 dropped) | `uncovered=[si-2]` only, orphan=0 | ✅ flags the exact dropped intent |
| `phantom/` (wu-2→si-999 ghost) | `phantom=[wu-2→si-999]`, uncovered=0 | ✅ catches the dangling edge (was untested) |
| `inprogress/` (no exec/verify) | uncovered=0, orphan=0, phantom=0; `unverified=[wu-1,wu-2]` | ✅ structurally sound, not yet done |

**DESIGN REFINEMENT surfaced (fold into D26 / 14-projection-engine):** the closure checks split into
TWO categories — **structural integrity** (`orphan`, `phantom`, `uncovered`, `duplicate-id`,
`stale-reference`, `forged-parsed`) which are *always* defects, vs **progress/completeness**
(`unverified`, `deleted-with-open-obligation`, `contradicted`) which are **phase-gated** — only a BLOCK
at the relevant phase-exit (Heartgate); mid-run they're informational, not failures. The spike's flat
"FAIL" conflates them; the real engine MUST distinguish, or every in-progress run false-fails
`unverified`. (Surfaced by the `inprogress` fixture — exactly what a half-done case is for.)

## Piece 1d — final-review remediation applied to the spike (2026-06-20)

Per the final delta review ([23-final-review.md](../23-final-review.md)), the spike was hardened:
- **`unverified` now requires `result == pass`** (was: ANY assessment counted → a `fail` assessment
  vacuously "verified" the work_unit). Fixed in `closure()`.
- **`contradicted` check added** — a `pass` assessment over a `fail`/absent evidence checkpoint. New
  fixture `contradicted/` → `[BLOCK] STRUCT contradicted 1 — as-1(pass) ← evidence cp-1=fail`, while
  `unverified=0` (the lie fools `unverified`; `contradicted` catches it). Demonstrates the gap reviewers flagged.
- **Structural-vs-progress labels** — checks now print `STRUCT` (always-block: uncovered/orphan/phantom/
  contradicted) vs `PROG` (phase-gated: unverified). Operationalizes the T2 refinement in-spike.
- **Legacy fixtures self-contained** — copied into `fixtures/legacy/`; `--dir` reproduces **9 uncovered /
  2 orphan** from co-located artifacts (was: not reproducible in the worktree — a dangling reference).
- **Real validator run** — `validate_proposal` (scripts/validate_uacp_artifacts.py:426) on the keyed
  `oauth-login/proposal.yaml`: the **`in_scope` check PASSES** (item-shape-agnostic, line 438). The other
  BLOCKs are fixture-minimalism (missing phase/title/objective/…), unrelated to keying — **proves the
  clean break (D32) does not break the real scope check.**


