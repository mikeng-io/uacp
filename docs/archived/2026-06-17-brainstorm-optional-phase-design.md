---
type: design
title: "Brainstorm as an Optional Kernel Phase — Design"
description: "Design for promoting `brainstorm` from an informal pre-TRIAGE skill to a formal, state-registered optional entry phase"
tags: ["brainstorm", "lifecycle", "phase", "kernel"]
timestamp: 2026-06-17
status: archived
---

# Brainstorm as an Optional Kernel Phase — Design

> Design doc (brainstorming output). One of three for this initiative:
> A = this (brainstorm phase) · B = lesson/knowledge corpus + distillation · C = Oracle retrieval engine.
> Implementable independently of B/C; the Oracle's advisory hook at brainstorm lands once C exists.

**Goal:** Make `brainstorm` a *formal but optional* entry phase of the UACP lifecycle — a real, state-registered phase the kernel knows about — rather than the informal pre-TRIAGE skill it is today.

> **Slice scope note (FIX-2):** For this slice, `brainstorm exits_to = {triage}` ONLY. The `brainstorm→terminal` (explore-and-bail) edge is a tracked follow-up: `state_machine_projection()` drops every `→terminal` edge, so the edge cannot be a real transition until the `aborted`-status path is designed. All references to `exits_to = {triage, terminal}` below are updated accordingly.

**Status:** Approved in brainstorming dialogue 2026-06-17. Not yet planned/implemented.

---

## Context — current reality

The codified grammar enumerates exactly six phases and treats `triage` as the sole entry:

- `engines/domain/phase_transitions.py`: `_PHASE_ORDER = ("triage","propose","plan","execute","verify","resolve")`; `STAGE_ENTERS_FROM["triage"] = ["none"]`, every other phase requires a predecessor. `brainstorm` appears in **none** of `STAGE_ALLOWED_TOOLS` / `STAGE_FORBIDDEN_TOOLS` / `STAGE_PHASE_EXIT_INVARIANTS` / `STAGE_PURPOSE`.
- `engines/domain/phase_graph.py`: `LIFECYCLE_GRAPH` has no `brainstorm` node.
- `skills/uacp-state/scripts/state_machine.py`: `RunManifest.current_phase` defaults to `"triage"`; `VALID_TRANSITIONS` has no brainstorm edges.
- `config/uacp.toml`: `[phases.*]` sections for the six; `[heartgate].allowed_transitions` lists only the six's edges. No `[phases.brainstorm]`.
- `skills/uacp-brainstorm/SKILL.md`: declares itself **informal** — "does not write formal UACP proposals, state records, or lifecycle artifacts"; holds **no** governed-writer tools; outputs a `uacp.brainstorm_scope_package` into `.uacp/brainstorm/`. Its `references/phase-8-admission.md` states: *"Brainstorm artifacts themselves are NOT registered in `uacp-state`."*

So brainstorm today is a coached exploration that produces a scope package and hands it to TRIAGE out-of-band. Nothing in the kernel models it.

## Design — formal, optional entry phase

Add `brainstorm` as a phase with `enters_from = ["none"]` and `exits_to = {triage}` (this slice), and make `triage` additionally enterable from `brainstorm`. A run may **start** at `brainstorm` *or* at `triage`; brainstorm is never required, and entering formal work always flows `brainstorm → triage` (it *precedes* triage, never skips it). Explore-and-bail (`brainstorm → abort`) is a follow-up requiring the `aborted`-status path to be designed first.

### Touch-points (all in skills/code)

1. **`engines/domain/phase_transitions.py`**
   - Prepend `"brainstorm"` to `_PHASE_ORDER`.
   - `STAGE_PURPOSE["brainstorm"]` — exploration / scope clarification.
   - `STAGE_ALLOWED_TOOLS["brainstorm"]` — `Read/Glob/Grep/Task/Write` **plus** the governed writers it now needs: `uacp_state_write`, `uacp_artifact_write`, `uacp_heartgate_check`, and (once Doc C lands) `uacp_oracle_query`.
   - `STAGE_FORBIDDEN_TOOLS["brainstorm"]` — anything that would mutate project state (it's exploratory).
   - `STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]` — the **admission contract** (today's `phase-8-admission` check, promoted to a real exit invariant): a selected scope-package artifact exists with non-empty `title`/`description`/`in_scope`, `declared_side_effects` present, `authority.source` documented, valid `routing_advisory`.
   - `STAGE_ENTERS_FROM["brainstorm"] = ["none"]`; change `STAGE_ENTERS_FROM["triage"] = ["none", "brainstorm"]`.

2. **`engines/domain/phase_graph.py`** — add `brainstorm → {triage}` to `LIFECYCLE_GRAPH` (this slice). `brainstorm → terminal` (explore-and-bail) is a follow-up — it requires the `aborted`-status path designed before `state_machine_projection()` can expose it.

3. **`skills/uacp-state/scripts/state_machine.py`** — allow `RunManifest.current_phase` to initialize at `brainstorm` *or* `triage`; add `VALID_TRANSITIONS` edge `brainstorm→triage` (derived automatically from `state_machine_projection()`; `brainstorm→terminal` is NOT added in this slice).

4. **`config/uacp.toml`** — add `[phases.brainstorm]` (`council_mode = "brainstorm"` — if the enum only accepts `research/design/plan/implement/audit`, reuse `"research"` as a stand-in); add ONLY `brainstorm->triage` to `[heartgate].allowed_transitions` (NOT `brainstorm->terminal`, which is not in `LIFECYCLE_GRAPH` for this slice).

5. **`skills/uacp-brainstorm/SKILL.md`** — gains the governed writers; on entry **registers a run** at `phase: brainstorm` (`uacp_state_write`), writes the scope package as a **real lifecycle artifact** (`uacp_artifact_write`), and runs `uacp_heartgate_check` for the `brainstorm→triage` transition. The skill's current "informal / not registered" stance and the `phase-8-admission` note are **replaced** — brainstorm artifacts are now state-persistent. (Oracle fires here in *advisory* mode once Doc C exists — see Doc C.)

6. **Agreement tests** — `tests/unit/uacp_core/test_phase_graph.py` (and any phase-order/transition fixtures) pin `brainstorm` into the graph, the new `brainstorm→triage` edge, and the dual `enters_from` for triage. Mutation-verify the new invariant is non-vacuous.

### Optionality & invariant reconciliation

- **Optional:** a run may begin at `triage` directly (today's default) or at `brainstorm`. The brainstorm phase is opt-in.
- **No phase-skipping:** `brainstorm → triage` is the only path into formal work, so brainstorm *precedes* TRIAGE rather than bypassing it. For this slice, `exits_to = {triage}` — there is no `brainstorm → terminal` edge. Explore-and-bail (stopping before any formal artifact) will use the `aborted`-status path once that is designed; it is tracked as an explicit follow-up and is NOT part of this slice.
- **Invariant text:** AGENTS.md's "TRIAGE-first / no phase-skipping" invariant will want a one-line clarification ("non-trivial work enters formal governance via TRIAGE; an optional brainstorm phase may precede it"). That is a **docs** edit, out of this skills-focused scope — tracked as a follow-up, not part of this slice.

## Testing

- Phase-graph agreement tests (above), mutation-verified.
- Transition tests: `none→brainstorm`, `brainstorm→triage`, and that `triage` still accepts `none` (direct entry) — plus that illegal edges (e.g. `brainstorm→plan`) are blocked. `brainstorm→terminal` is NOT tested in this slice (explore-and-bail via the abort-status path is a tracked follow-up).
- Heartgate test: a `brainstorm→triage` transition with a conformant scope-package artifact PASSES; a missing/under-specified package BLOCKS (the exit invariant bites).
- Skill-readiness lint already covers frontmatter/`kind`; confirm `uacp-brainstorm` stays conformant after gaining writers.

## Risks / open items

- **Run-registry semantics:** decide whether a brainstorm-only run (that aborts before triage) registers in `run-registry.yaml` or stays a lightweight pointer. Recommendation: register it (traceable, resumable) but mark it non-advancing. This is deferred together with the explore-and-bail follow-up.
- **Bridging the old `.uacp/brainstorm/` layout** to the registered-artifact layout — a small migration in the skill body.
- **Invariant doc clarification** (above) — separate docs follow-up.
