# 09 — Grounding-retarget experiment (B1 viability proof)

Decision experiment that un-parks this bundle. It tests the council's central blocker
([08-review-findings](08-review-findings.md)): *does moving prose to Markdown silently break the
gates that read it?* — on the hardest such gate, `validate_class_underclaim`. Commit `da86643`
(the P0 experiment) and Slices 1–2 are now MERGED to main (PR #70 / `c7bd737` / 2026-06-29).
Suite green, additive.

## 1. What was the plan

Prove or kill **B1** (MD = semantic content; YAML = relations) on the single hardest case before
committing the bundle, rather than re-litigating the design in prose. `validate_class_underclaim`
(in `manifest/projection.py`) is the worst case because it **comprehends in code**: it keyword-greps
the target's own prose (`intent` / `expected_outputs` / `statement`) via `candidate_class()` to
derive a class, then blocks if the agent's declared class is weaker. If
*this* gate can be converted from "read prose" to "measure a relation" without losing teeth, the
pattern generalises to every prose-reading gate (D43, `scope.statement`). Four steps:

1. **baseline** — confirm the gate fires on a genuine underclaim today (it has teeth).
2. **dark regression** — simulate B1 (prose → MD, gone from the projected node) and show the gate
   goes *silently* toothless. Make the council's abstract warning runnable.
3. **retarget** — feed an independent `entailed_class` oracle and restore the catch with **no prose
   read**.
4. **residual** — remove *both* prose and the oracle; observe what's lost; decide whether a
   semantic witness is required.

## 2. What was the outcome

**Verdict: B1 is viable for the hardest prose-reading gate.** The retarget works, additively
(legacy prose path intact), zero regressions. Three findings, in order of importance:

- **The gate is an INDEPENDENCE check, not a prose check.** The prose keyword-match was only a
  *cheap independent oracle that happened to live in the YAML the gate could read*. What gives the
  gate teeth is having *some* derivation of the true class the agent does not control. Remove prose
  *and* provide no other oracle (step 4) → the catch is gone. So a naive agent-declared field
  preserves nothing; the oracle MUST be sourced independently.
- **The retarget pattern.** Agent makes a **claim** (declared class on its checks); an **independent
  witness** derives the truth; the **code only compares** claim-vs-witness and blocks on mismatch.
  The gate never decides truth — it measures grounding. This is `comprehend → measure` with the
  measure pinned to a relation, not prose.
- **Two witnesses, combined by a fixed rule — never another agent.** (1) **codeflair** = code reads
  code (deterministic FLOOR — a wiring edge in the real graph; cannot be overridden). (2) a
  **semantic witness** (independent reviewer / small model) = escalate-only CEILING (may raise the
  class, never lower the floor). Synthesis is `max(floor, ceiling)` vs declared, **in code**. An
  agent that could *combine* could talk the deterministic floor away — so the combiner is never an
  agent.

## 3. What was the measurement

Evidence, not assertion. Commit `da86643`, now MERGED (PR #70 / `c7bd737` / 2026-06-29):

| signal | result |
|---|---|
| existing underclaim suite (6 tests) | pass — baseline gate fires on genuine underclaim |
| `test_PROTO_underclaim_dark_regression_when_prose_relocates_to_md` | pass — same underclaim, prose in MD → gate **silently passes** (regression reproduced) |
| `test_PROTO_retarget_restores_teeth_via_entailed_class_without_prose` | pass — teeth restored, `oracle_source == "entailed_class"` (no prose read) |
| `test_PROTO_independence_is_the_crux_no_oracle_no_catch` | pass — no prose + no oracle → no catch (independence proven) |
| full suite | **2202 passed, 8 skipped** (additive — legacy prose path untouched) |
| `ruff check` | clean |

Non-vacuity is structural: the dark-regression test fails if the gate *doesn't* regress; the
retarget test fails if teeth *aren't* restored; the residual test fails if a non-independent field
*were* enough.

## Honest limit

`entailed_class` is **test-injected** here — the test plays the oracle. What is proven is the gate
mechanics + the independence finding. Wiring **codeflair** as the real producer is unproven and is
the next build ([10-implementation-roadmap](10-implementation-roadmap.md)).
