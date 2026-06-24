---
kind: uacp.handoff
workstream: verification-method
timestamp: 2026-06-25
status: paused
worktree: /Users/mike/Workplace/uacp/.worktrees/verification-method
branch: verification-method   # UNPUSHED
---

# Handoff — verification-method (resume sharp)

## UPDATE 2026-06-25 — Build #1 FINALIZE HALF LANDED (uncommitted)
The closure sweep is now wired onto the live finalize path. `state_machine.handle_finalize`
tentatively finalizes → runs `Heartgate.validate_closure` (via `_run_closure_gate`, lazy
import to avoid the engines↔state_machine cycle) → **blocks + reverts `finalized_at`** on any
engine blocker; **fail-closed** (an unrunnable gate blocks). TDD keystone:
`tests/e2e/test_finalize_closure_gate.py` proves a finalize that returned `ok` today (corrupted
ledger → `LI_TIMESTAMP_NON_MONOTONIC`) is now blocked THROUGH `handle_finalize`, `finalized_at`
reverted to None; a closeable run still finalizes. Ripple = correct lifecycle ordering: the
happy-path helpers now author+register the **lessons (closure) artifact BEFORE finalize**
(`drive_happy_path(..., finalize=False)`, `_author_and_register_lessons`, test_full_lifecycle
authors lessons pre-finalize); unit `test_finalize_blocked_when_run_not_closeable` asserts a bare
run is refused (C4) + reverted. **Suite 1873 green, changed files ruff-clean, branch still UNPUSHED + UNCOMMITTED.**

**Transition half NOT built — mike chose STOP after the finalize half.** Grounded reason the
literal "force `validate_transition` via the PreToolUse hook on writes to transition artifacts"
does NOT close the hole: `validate_closure` reads EMITTED RUN-STATE (clean to wire at the finalize
chokepoint), but `validate_transition` validates a SUPPLIED PACKAGE and `handle_transition` (the
universal phase-advance chokepoint) never consults one — a hook-on-writes guard only hardens
package-LANDING while an agent can still advance a phase via `handle_transition` with no package.
The robust closer = a **state-derived per-transition gate inside `handle_transition`** (analogous
to closure) — a small new gate, not a one-line hook branch, overlapping #2 below. Do NOT ship the
fragile hook guard. **NEXT: that transition gate, then #2 (feed the coverage gate).**

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
