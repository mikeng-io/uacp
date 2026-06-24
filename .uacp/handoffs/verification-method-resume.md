---
kind: uacp.handoff
workstream: verification-method
timestamp: 2026-06-25
status: paused
worktree: /Users/mike/Workplace/uacp/.worktrees/verification-method
branch: verification-method   # UNPUSHED
---

# Handoff — verification-method (resume sharp)

## UPDATE 2026-06-25 (session 2) — Builds #1 + transition gate LANDED; Step 2 = design node authored. 3 commits, branch UNPUSHED.

**Commit `ad8026d` — finalize closure gate (Build #1 finalize half).** `state_machine.handle_finalize`
tentatively finalizes → runs `Heartgate.validate_closure` (via `_run_closure_gate`, lazy import to
avoid the engines↔state_machine cycle) → **blocks + reverts `finalized_at`** on any engine blocker;
**fail-closed**. Keystone `tests/e2e/test_finalize_closure_gate.py`: a finalize that returned `ok`
(corrupted ledger → `LI_TIMESTAMP_NON_MONOTONIC`) is now blocked THROUGH handle_finalize, reverted.
Ripple = correct RESOLVE ordering: happy-path helpers author the lessons artifact BEFORE finalize
(`drive_happy_path(..., finalize=False)`, `_author_and_register_lessons`); unit test asserts a bare
run is refused (C4) + reverted.

**Commit `e3f6834` — transition structural gate (the robust transition fix).** Earlier I surfaced
that the literal "force validate_transition via the PreToolUse hook" does NOT close the hole
(validate_transition needs a SUPPLIED PACKAGE; handle_transition never consults one). The robust
closer turned out to ALREADY EXIST: `validate_graph_invariants(run_id, '<from_phase>_exit')` (D35,
phase-scoped structural subset) — wired only into the agent-invoked `validate_transition` via
`phase_exit.py`. So I FORCED it onto the live path: `handle_transition` now runs it (lazy import)
BEFORE advancing, for `from_phase ∈ {plan,execute,verify}`, phase-independent (no revert),
fail-closed; `from_phase` is already checked vs `current_phase` so the scope is not forgeable.
Keystone `tests/e2e/test_transition_graph_gate.py`: a plan with a phantom `derives_from` edge is
blocked (`GP_PHANTOM_EDGE`) at plan→execute; clean plan advances. Phantom/obligation-coverage have
teeth NOW; uncovered/orphan (dropped intent) await Step 2.

**Commit `7d682a3` then CORRECTED by `f2c851d` — Step 2 design node (mike chose "design-node first").**
`7d682a3` authored `design/verification-method/15-coverage-serialization.md` but got the framing
WRONG (claimed "no real producer emits keyed scope_items + derives_from; D43 unbuilt"). An
independent review (cross-provider **kimi** + a **Claude subagent**, both grounded in code, mike
asked for it) caught it as FALSE and I verified: **D43 producer-serialization is ALREADY BUILT** —
`engines/domain/schema.py` requires keyed `scope.in_scope:[{id,statement}]` at write time +
`derives_from` on PIV work_units; `scripts/validate_uacp_artifacts.py` (validate_proposal /
validate_piv_contract); entity-writer validate-on-write; propose/plan SKILL contracts; passing
`tests/integration/test_graph_gate_activation_e2e.py`. My original grounding (only the
package-selection seeders + projection.py) missed all of it. `f2c851d` corrected node 15 + `_index`
+ fixed the now-stale `validate_closure` docstring (it still said "NOT auto-called by handle_finalize"
— ad8026d made that false).

**The REAL residual (corrected):** the kernel's gate-REQUIRED PROPOSE artifact is
`uacp.proposal_package_selection` (scope in MARKDOWN), NOT the keyed `uacp.proposal` — so coverage
does NOT bind for the package-selection representation (the path the lifecycle fixture uses;
documented at schema.py). Open decision = close that residual: (1) add machine-readable `scope_items`
to `uacp.proposal_package_selection` + enforce in `validate_proposal_package_selection` (less
disruptive, reviewers' pick) OR (2) make the KERNEL require `uacp.proposal` (today only SKILLs do).
Plus 3 verified blind spots in node 15: `inherited_artifacts` invisible to `projection._load_and_project`
(goal-driven coverage bypass); no transition-time referential check that `derives_from` ids resolve;
topology-only gate is gameable (point all work_units at one throwaway scope_item).

**Session 2b — residual fixes (suite 1878 green).** Mike chose D43 **Option C** (keyed scope module +
register PIV). Grounded follow-up: `entity_writer.create_entity` AUTO-REGISTERS every `uacp_entity_write`
into `manifest.artifacts` — so governed runs writing a keyed `uacp.proposal` + PIV already register+project
both and coverage is **enforced on the live path**. Commits: `18ad3a8` (fix #2: `projection._load_and_project`
now projects `inherited_artifacts` so goal-chained runs can't bypass coverage; TDD); `b1c32f9`
(`tests/e2e/test_transition_coverage_enforced.py` proves a governed run with a DROPPED intent is BLOCKED by
`handle_transition(plan→execute)` with `GP_UNCOVERED_INTENT`; covered advances; node 15 records Option C).
#3 (referential check) DEFERRED (redundant w/ GP_PHANTOM_EDGE); #4 (gameable) = council/semantic scope.

**Enforcement increment LANDED (mike: do it now).** `validate_adaptive_proposal_package_gate` now REQUIRES
the `scope` concern be `covered` by a keyed scope module (`scope.in_scope:[{id,statement}]`); na/markdown
scope is a blocker (`_scope_concern_is_keyed`). Structured intent scope is now mandatory for governed
package-selection PROPOSE→PLAN. TDD `tests/e2e/test_proposal_scope_gate.py` (non-vacuity proven); shared
`_seed_proposal_package` emits a keyed scope module (one fix cascade-cleared 49 fixtures). Suite **1881 green**.

**Session 2c — keystone landed:** `fix(verify): GP_UNCOVERED fires on scope PRESENCE` — `_check_uncovered`
self-gates on scope-presence (skip only when NO scope_item nodes), not on `_coverage_adopted`, so a run that
declares intents but covers NONE is caught (matches the projection docstring). `_check_orphan` stays
adoption-gated. One unit test updated. Suite **1881 green**.

**NEXT SESSION = implement OPTION B for full package-selection BINDING (decided).** Gap: a package-selection
run's scope_items (referenced scope module) + work_units (PIV) are REFERENCED-not-REGISTERED, so
`projection._load_and_project` (reads only `manifest.artifacts`) never projects them → the forced plan_exit
gate has nothing to check. **Option B (chosen over A=projection-follows-canonical-paths, which changes the
registered-state-only principle + ripples every e2e run w/ phantom-flood risk):** require REGISTRATION —
scope module registered at PROPOSE (extend the adaptive proposal scope check to require it in
`manifest.artifacts`) + PIV registered at PLAN; seeders register them; **projection UNCHANGED**. Then forced
plan_exit GP_UNCOVERED fires for package-selection too. WATCH-OUT: keystone now fires uncovered on
scope-presence → the happy-path PIV must COVER its scope module's si-1 (align `_seed_governed_run` /
`_seed_proposal_package`), else happy path breaks. TDD: a package-selection dropped intent blocks at FORCED
plan_exit (not just validate_transition). Then capsule #3 (the generator). Branch UNPUSHED (~14 commits;
not asked to push).

---

## TL;DR (read this first)
After a long session the **net real change is ~3 lines** — an execution failure, not the work being tiny. The design got re-grounded (docs), one kernel slice was built-then-reverted, and a cosmetic council edit landed. **A grounded audit found the actual flaw.** Resume by building **#1 below** (small + real). Do NOT build more peripheral/cosmetic pieces.

## THE KEY FINDING (the real #503-class hole)
UACP's strongest verification — `validate_closure` → `run_all_engines` (the full engine sweep: coherence, evidence_completeness, GP_CONTRADICTED, ledger_integrity, scope_conformance, …) — has **ZERO runtime callers**. It runs **only in tests** (`engines/heartgate/heartgate.py:248`; its own docstring admits "not auto-called"). And `validate_transition` is **agent-invoked, not forced** (the Guardian PreToolUse hook resolves phase for policy but never calls Heartgate; nothing compels `uacp_heartgate_check` at a transition). So **the best checks the system owns aren't wired to the live path** — the macro form of #503 class-A fail-open ("the check was never run and nothing noticed"). This, not missing checks, is why verification is foolable.

## What to build (prioritized — from the grounded failure-class→closure audit)
1. **[SMALL, highest value, structural] Wire the closure sweep onto the live path.** Call `validate_closure` from `state_machine.handle_finalize` (RESOLVE), and force `validate_transition` via the Guardian PreToolUse hook on writes to transition artifacts. The code exists — this is wiring + one hook branch. Closes the practical fail-open. **DO THIS FIRST.** TDD: a run that finalizes without the sweep must now be blocked; assert the sweep actually fires at finalize.
2. **[SMALL/MED, structural-on-producer] Feed the coverage gate.** `GP_UNCOVERED_INTENT`/`GP_ORPHAN_WORK_UNIT` **silently SKIP** because PROPOSE/PIV don't emit keyed `scope_items` + `derives_from` edges (`engines/manifest/projection.py:177` `_coverage_adopted`; the D43 gap). Make PROPOSE emit keyed scope_items and PIV emit `derives_from` → the dropped-intent detector binds. No new check logic, just producer serialization.
3. **[LARGE, genuinely new] The generator.** Author a deterministic check *from artifact content* + replay it (closes #503 classes B weak-proxy / C-behavioral reality-binding / F-content drift). Needs a serialized assertion `kind` in `engines/domain/schema.py` + a replay engine (the `Engine`/`Violation` model is the sink) + (for behavioral BIND) the Code/SCIP plane. This is the heart of the initiative; gate it behind #1+#2.

## State of the branch (commits)
- `3d632d1` — re-ground the 8-node bundle vs merged CMS + as-built engines (coherent, validated, suite 1871 green). KEEP.
- `7ea78f6` — council verification-gate posture (default-to-refute + majority-clear) in `uacp-council/references/finding-driven-mode.md` + a 1-line `uacp-verify/SKILL.md` pointer. Cosmetic (procedural, agent-trusted). KEEP but it is NOT the fix.
- A kernel slice (EXECUTE generate-exclusion) was built then **reset away** (was `ff7ffb0`): it shipped a **dead guard** (I edited `governed_handlers.py` in the WRONG worktree — LSP pointed at the primary checkout) AND is fragile even when wired (forgeable `uacp_phase` token; needs a run-state-derived phase). PARKED until a trustworthy-phase substrate exists. The pure policy idea (`generation_exclusion_violation`, kind-home-derived) is sound and recorded in node 12's "to build".

## Procedural-not-structural gaps (trust the agent, NOT enforced — candidates to harden later)
default-to-refute council posture; the EXECUTE `exclusions:[generate]` rule; the self-approval guard; "don't normalize findings to pass." All live in the verify SKILL as prose; a non-compliant agent bypasses them silently.

## Lessons locked this session (don't repeat)
- **Build the thing that fixes the flaw, not the smallest/cosmetic piece.** The 3-line whipsaw was the failure.
- **Work IN the target worktree** — verify `pwd`/paths before every edit; LSP roots at the PRIMARY checkout and will send you there (that caused the dead-guard bug). See memory `work-in-worktree-not-branch-in-main-checkout`.
- **Prompt reviewers fuzzy/intent-first, not detailed-checklist** — give intent + artifact + grounding, let them find inconsistencies; a checklist makes them grade your rubric. See memory `reviewer-prompts-fuzzy-intent-not-checklist`.
- **Most of verification IS already built + well-built** (the engine substrate, the per-phase graph gate, fail-closed ppv/plan_validation/adaptive gates, ledger integrity, watermarking). The initiative is genuinely mostly-assembly — the gaps are #1 wiring, #2 feeding, #3 generator.

## Restart instruction for the fresh session
Open the worktree above. Read this capsule + memory `uacp-verification-method-initiative`. Then build **#1 (wire `validate_closure` + force the transition gate)** TDD — the smallest change that measurably makes verification harder to fool. The suite is green at 1871; primary worktree is clean (the stray edit was reverted).
