---
type: plan
title: "UACP Goal-Driven Track — Implementation Plan"
description: "9-task implementation plan for the `goal-driven` lifecycle track with persistent goal, checkpoint manifest, and convergence budget"
tags: ["goal-driven", "lifecycle", "track", "checkpoint"]
timestamp: 2026-06-16
status: archived
---

# UACP Goal-Driven Track — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: superpowers:executing-plans (or superpowers:subagent-driven-development for same-session). Two-stage review per task. This touches kernel enforcement — smallest steps, behavior-preserving for the **standard track** (production-equivalence bar, exactly like the config-collapse slices). Suite green after every task (current baseline: `python3 -m pytest tests/ -q` → 516 passed, 2 skipped).

**Goal:** Add a second lifecycle **track** — `goal-driven` — so semantic/exploratory work is governable under the *same* five phases, realized as a **persistent goal anchoring a chain of forward runs** plus an **in-EXECUTE checkpoint manifest**. The existing (`standard`) track is provably unchanged.

**Architecture (from design + ADR-0016, P2=b):** The phase graph is **NOT** touched — per-run transitions stay forward-only in both tracks. TRIAGE sets a `track` field via a mechanical test. A `goal-driven` run carries a `goal_id`; "roll back to PLAN/PROPOSE" = launching a *new forward run* under the same held goal, reusing the prior phase's output (no in-run rewind, no graph back-edge). Each EXECUTE iteration writes a gate-ledger-backed, non-self-attesting **checkpoint manifest** entry whose `evidence` references a real artifact. A required **convergence budget** bounds autonomous runs.

**Tech stack:** `python3` (3.14 — NOT anaconda `python`). Lint `/Users/mike/.local/bin/ruff check` (E,F,I,UP,B). Tests `python3 -m pytest tests/ -q`. Pydantic v2 models in `skills/uacp-core/scripts/engines/domain/`.

**Read first:** `docs/plans/2026-06-16-uacp-goal-driven-track-design.md` + `docs/architecture/0016-goal-driven-track.md`.

**Naming decisions baked in (O1, O4):** track enum = `standard` | `goal-driven` (default `standard`). The iteration unit is a **checkpoint** (not "build").

**THE load-bearing invariant for every task:** a run with no `track` (or `track: standard`) and no `goal_id` MUST behave byte-identically to today. Default everything; gate every new behavior behind `track == "goal-driven"`. Pin it (Task 8).

---

# Task 1: TRIAGE `track` field + mechanical selection test

**Files:**
- Modify: `scripts/validate_uacp_artifacts.py` (`validate_triage` ~409) — accept + validate `track`.
- Modify: `skills/uacp-triage/SKILL.md` — document the selection test + the `track` field.
- Test: `tests/unit/uacp_core/test_triage_track.py` (new) — or extend existing triage tests.

**Step 1 (failing test):** `validate_triage` accepts `track: standard` and `track: goal-driven`; rejects `track: bogus` with a BLOCK; treats an ABSENT `track` as `standard` (back-compat, no BLOCK).
**Step 2:** run → fails (no track handling).
**Step 3:** in `validate_triage`, read `obj.get("track", "standard")`; BLOCK if not in `{"standard","goal-driven"}`. Do NOT make `track` a required field (absent = standard).
**Step 4:** in `uacp-triage/SKILL.md`, document the mechanical test: *"Is the success criterion specifiable as a verifiable artifact before EXECUTE? yes → standard; no → goal-driven,"* and that TRIAGE records `track` on the triage artifact.
**Step 5:** suite green + ruff. Commit `feat(triage): add track field (standard|goal-driven) + mechanical selection test`.

# Task 2: RunManifest carries `track`, `goal_id`, `inherits_from` (additive, defaulted)

**Files:**
- Modify: `skills/uacp-state/scripts/state_machine.py` (`RunManifest` ~75; `handle_init` ~125).
- Test: `tests/unit/uacp_state/test_state_machine.py` (extend).

**Step 1 (failing tests):** (a) a `RunManifest` with no new fields validates and serializes exactly as today (equivalence); (b) `handle_init` accepts optional `track`/`goal_id`/`inherits_from` args and persists them; (c) defaults: `track="standard"`, `goal_id=None`, `inherits_from=None`.
**Step 3:** add three fields to `RunManifest` with defaults (`track: str = "standard"`, `goal_id: str | None = None`, `inherits_from: str | None = None`). Thread through `handle_init` (read from args, pass to the constructor). Keep `model_dump(mode="json")` stable for standard runs (defaults must not change existing serialized output for runs that don't set them — verify the equivalence test).
**Step 5:** suite green + ruff. Commit `feat(state): RunManifest gains optional track/goal_id/inherits_from (defaulted, standard unchanged)`.

# Task 3: Persistent goal + run-chaining ("roll back" = new forward run under the held goal)

**Files:**
- Modify: `skills/uacp-state/scripts/state_machine.py` (`handle_init`) — support launching a run *under an existing goal*, inheriting a prior run's PROPOSE/PLAN artifact references + the frozen goal.
- Modify: `skills/uacp-core/scripts/engines/domain/registry.py` — `RunRegistryEntry` gains optional `goal_id` (extra=allow already tolerates it; make it typed).
- Modify: `skills/uacp-state/scripts/state.py` (`_handle_uacp_run_registry_update` ~225) — preserve caller-binding; allow recording `goal_id` on the entry.
- Test: `tests/unit/uacp_state/test_goal_chain.py` (new).

**Step 1 (failing tests):** (a) `handle_init(..., goal_id="g1", inherits_from="run-A")` creates run-B that copies run-A's frozen goal + its declared PROPOSE/PLAN artifact refs into run-B's manifest (the reused output), and links `inherits_from="run-A"`; (b) the run-registry can hold multiple active entries sharing one `goal_id` (the chain is queryable by goal); (c) a `standard` run (no goal_id) is unaffected.
**Step 3:** implement the inherit-on-init: when `goal_id`+`inherits_from` are present, load the parent manifest, copy the goal statement + the named prior-phase artifact references into the new manifest (do NOT copy mutable execution state — only the frozen goal + the chosen reused phase output), set `inherits_from`. Type `goal_id` on `RunRegistryEntry`. Keep caller-binding in the registry writer.
**Step 5:** suite green + ruff. Commit `feat(state): goal-anchored run chaining — launch a forward run under a held goal reusing prior phase output`.

# Task 4: In-EXECUTE checkpoint manifest (gate-ledger-backed, non-self-attesting)

**Files:**
- Create: `skills/uacp-core/scripts/engines/domain/checkpoint.py` — the `CheckpointEntry` model.
- Modify: `skills/uacp-core/scripts/engines/domain/__init__.py` — export it.
- Modify: `skills/uacp-core/scripts/core.py` (Heartgate) — a `_validate_checkpoint_entry` that enforces the no-self-attestation + external-evidence-ref rule, mirroring the existing gate-ledger checks.
- Modify: `skills/uacp-state/scripts/state.py` (`_handle_uacp_gate_ledger_append` ~60) — accept `gate: "CHECKPOINT"` records (no new writer; reuse the governed ledger writer).
- Test: `tests/unit/uacp_core/test_checkpoint_manifest.py` (new).

**Checkpoint entry schema (from design):** `checkpoint_id` · `run_id` · `goal_id` · `phase` (=execute) · `what_changed` · `why` · `evidence` (a governed-root-relative artifact path that MUST exist) · `verdict` ∈ `{keep, roll_back, restart}` · `invariant` · `rolled_back_to` (checkpoint_id | null).

**Step 1 (failing tests):** (a) a checkpoint whose `evidence` references an existing artifact under the governed root passes; (b) a checkpoint with prose-only / missing / out-of-root `evidence` is BLOCKED (the no-self-attestation rule — claim requires a real evidence artifact); (c) entries route through `uacp_gate_ledger_append` (a direct `uacp_state_write` under `state/gate-ledger/` is still refused).
**Step 3:** implement `CheckpointEntry` + `_validate_checkpoint_entry` (resolve the `evidence` path with the existing `_artifact_path_exists` / governed-root containment helpers in core.py; reuse the gate-ledger append path). This is the *structural claim⇒evidence coupling* from ADR-0016 applied at the checkpoint boundary.
**Step 5:** suite green + ruff. Commit `feat(heartgate): in-EXECUTE checkpoint manifest — gate-ledger-backed, evidence-ref required, no self-attestation`.

# Task 5: Required convergence budget for goal-driven runs

**Files:**
- Modify: `skills/uacp-core/scripts/core.py` (Heartgate PROPOSE-exit / the goal-driven run start) — require a `convergence_budget` and enforce the cap.
- Modify: `engines/domain` (the budget model, likely on the goal/PROPOSE artifact) + the relevant validator.
- Test: `tests/e2e/test_goal_driven_budget.py` (new).

**Step 1 (failing tests):** (a) a `goal-driven` run whose PROPOSE artifact lacks a `convergence_budget` (max_checkpoints + optional spend/wall-clock) is BLOCKED at PROPOSE→PLAN; (b) a `standard` run with no budget is unaffected (track-gated); (c) when the checkpoint count for a goal reaches `max_checkpoints`, a further `keep`/continue checkpoint is BLOCKED (forces converge or escalate).
**Step 3:** gate the requirement behind `track == "goal-driven"`. Count CHECKPOINT ledger entries per `goal_id` for the cap. Operator sign-off remains the interactive exit; the budget is the autonomous exit.
**Step 5:** suite green + ruff. Commit `feat(heartgate): goal-driven runs require + enforce a convergence budget (autonomous-safe)`.

# Task 6: Per-track validator relaxation (O2) — structural coupling stays

**Files:**
- Modify: `skills/uacp-core/scripts/core.py` (the PIV / findings-clearing gates) — make them track-aware.
- Test: `tests/e2e/test_goal_driven_gates.py` (new).

**Step 1 (failing tests):** for a `goal-driven` run: (a) authority / write-containment / no-fabrication invariants STILL fire (unchanged); (b) the deterministic findings-clearing / PIV-style gate is SATISFIED by a coherent checkpoint manifest (with real evidence refs) in place of the standard PIV artifact — but is BLOCKED if the manifest is incoherent or its evidence is missing; (c) a `standard` run's gates are byte-identical to today (track-gated relaxation only).
**Step 3:** read the run's `track`; for `goal-driven`, route the PIV/findings gate to accept the checkpoint manifest as the evidence substrate (NOT a bypass — the structural claim⇒evidence coupling from Task 4 is what's checked). Keep authority/containment/no-fabrication paths shared/unchanged.
**Step 5:** suite green + ruff. Commit `feat(heartgate): track-aware gate relaxation for goal-driven (manifest substitutes for PIV; invariants stay)`.

# Task 7: Promotion semantics + VERIFY/RESOLVE close (O5)

**Files:**
- Modify: `skills/uacp-core/scripts/core.py` (VERIFY/RESOLVE closure for goal-driven).
- Test: `tests/e2e/test_goal_driven_close.py` (new).

**Step 1 (failing tests):** a `goal-driven` run closes at VERIFY/RESOLVE only when **manifest coherence** holds — define it concretely: (a) the final checkpoint's `verdict == keep`, (b) no open `roll_back`/`restart` left dangling, (c) the final checkpoint's `evidence` exists and is bound to the goal, (d) the standard no-fabrication / containment closure invariants still pass. A run with an incoherent manifest (open roll-back, missing final evidence) is BLOCKED from RESOLVE.
**Step 3:** implement `_validate_goal_driven_closure` (manifest coherence as above) wired into the existing closure path, track-gated. "manifest coherence" is NOT a lower bar — it ADDS to the shared closure invariants.
**Step 5:** suite green + ruff. Commit `feat(heartgate): goal-driven promotion + close on manifest coherence (not a lower bar)`.

# Task 8: Standard-track production-equivalence guard (the safety net)

**Files:**
- Test: `tests/unit/uacp_core/test_standard_track_equivalence.py` (new).

**Step 1:** a test that drives a representative standard-track run end-to-end (or asserts the key gate outputs) and pins that with no `track`/`goal_id` set, behavior is identical to pre-feature — e.g. required_fields enforcement, transition allow/deny, PIV gate firing all match the standard path. Also assert: the phase graph (`phase_graph.LIFECYCLE_GRAPH`) is unchanged (no new edges) — the feature added no graph mutation.
**Step 3:** n/a (pure pin).
**Step 5:** full suite green (516/2 + all new tests) + ruff on every changed `.py`. Commit `test(goal-driven): pin standard-track production-equivalence + phase-graph-unchanged`.

# Task 9: Final gate + council + finish

- Suite + ruff (all changed `.py`) + residual scan: standard track unchanged; phase graph not mutated; every new behavior is `track == "goal-driven"`-gated; the checkpoint manifest is non-self-attesting.
- **Council (≥2 lenses):** (1) **standard-track-equivalence auditor** — no standard-track behavior changed; phase graph untouched; (2) **devil's advocate** — the goal-driven gates can't be used to dodge rigor (authority/containment/no-fabrication provably still fire; budget enforced; manifest evidence-refs real, not prose). Zero material findings unresolved.
- Finish: merge `--no-ff`, re-verify on main, update memory + the decision-log (status proposed → accepted).

---

## Self-review / sequencing notes
- Order is dependency-driven + standard-track-safe: schema/fields first (1–3, all defaulted), then the goal-driven-only behaviors (4–7, all `track`-gated), then the equivalence pin (8).
- Every goal-driven behavior is gated on `track == "goal-driven"`; a standard run never enters the new code paths. Task 8 is the tripwire.
- Open data-model choices the implementer finalizes (with the design as the contract): exact storage of the goal→run-chain (registry `goal_id` vs a small `state/goals/` index), and where `convergence_budget` lives on the PROPOSE artifact. Keep both governed-writer-only.
- This is `proposed` work — confirm with the operator before EXECUTE; O2's relaxation reuses the ADR-0016 structural-coupling finding (no Hermes detour).
