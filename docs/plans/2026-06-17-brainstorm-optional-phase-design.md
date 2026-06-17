# Brainstorm as an Optional Kernel Phase — Design

> Design doc (brainstorming output). One of three for this initiative:
> A = this (brainstorm phase) · B = lesson/knowledge corpus + distillation · C = Oracle retrieval engine.
> Implementable independently of B/C; the Oracle's advisory hook at brainstorm lands once C exists.

**Goal:** Make `brainstorm` a *formal but optional* entry phase of the UACP lifecycle — a real, state-registered phase the kernel knows about — rather than the informal pre-TRIAGE skill it is today.

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

Add `brainstorm` as a phase with `enters_from = ["none"]` and `exits_to = {triage, terminal}`, and make `triage` additionally enterable from `brainstorm`. A run may **start** at `brainstorm` *or* at `triage`; brainstorm is never required, and entering formal work always flows `brainstorm → triage` (it *precedes* triage, never skips it).

### Touch-points (all in skills/code)

1. **`engines/domain/phase_transitions.py`**
   - Prepend `"brainstorm"` to `_PHASE_ORDER`.
   - `STAGE_PURPOSE["brainstorm"]` — exploration / scope clarification.
   - `STAGE_ALLOWED_TOOLS["brainstorm"]` — `Read/Glob/Grep/Task/Write` **plus** the governed writers it now needs: `uacp_state_write`, `uacp_artifact_write`, `uacp_heartgate_check`, and (once Doc C lands) `uacp_oracle_query`.
   - `STAGE_FORBIDDEN_TOOLS["brainstorm"]` — anything that would mutate project state (it's exploratory).
   - `STAGE_PHASE_EXIT_INVARIANTS["brainstorm"]` — the **admission contract** (today's `phase-8-admission` check, promoted to a real exit invariant): a selected scope-package artifact exists with non-empty `title`/`description`/`in_scope`, `declared_side_effects` present, `authority.source` documented, valid `routing_advisory`.
   - `STAGE_ENTERS_FROM["brainstorm"] = ["none"]`; change `STAGE_ENTERS_FROM["triage"] = ["none", "brainstorm"]`.

2. **`engines/domain/phase_graph.py`** — add `brainstorm → {triage, terminal}` to `LIFECYCLE_GRAPH` (`terminal` = explore-and-bail without proposing).

3. **`skills/uacp-state/scripts/state_machine.py`** — allow `RunManifest.current_phase` to initialize at `brainstorm` *or* `triage`; add `VALID_TRANSITIONS` edges `brainstorm→triage`, `brainstorm→terminal`.

4. **`config/uacp.toml`** — add `[phases.brainstorm]` (`council_mode = "brainstorm"`, `auto_execute_bounded`, `council_at_start/end` per the defaults pattern); add `brainstorm->triage` and `brainstorm->terminal` to `[heartgate].allowed_transitions`.

5. **`skills/uacp-brainstorm/SKILL.md`** — gains the governed writers; on entry **registers a run** at `phase: brainstorm` (`uacp_state_write`), writes the scope package as a **real lifecycle artifact** (`uacp_artifact_write`), and runs `uacp_heartgate_check` for the `brainstorm→triage` transition. The skill's current "informal / not registered" stance and the `phase-8-admission` note are **replaced** — brainstorm artifacts are now state-persistent. (Oracle fires here in *advisory* mode once Doc C exists — see Doc C.)

6. **Agreement tests** — `tests/unit/uacp_core/test_phase_graph.py` (and any phase-order/transition fixtures) pin `brainstorm` into the graph, the two new edges, and the dual `enters_from` for triage. Mutation-verify the new invariant is non-vacuous.

### Optionality & invariant reconciliation

- **Optional:** a run may begin at `triage` directly (today's default) or at `brainstorm`. The brainstorm phase is opt-in.
- **No phase-skipping:** `brainstorm → triage` is the only path into formal work, so brainstorm *precedes* TRIAGE rather than bypassing it. `brainstorm → terminal` lets a run explore and stop **before** any formal artifact is produced — no governance was entered, so nothing is skipped.
- **Invariant text:** AGENTS.md's "TRIAGE-first / no phase-skipping" invariant will want a one-line clarification ("non-trivial work enters formal governance via TRIAGE; an optional brainstorm phase may precede it"). That is a **docs** edit, out of this skills-focused scope — tracked as a follow-up, not part of this slice.

## Testing

- Phase-graph agreement tests (above), mutation-verified.
- Transition tests: `none→brainstorm`, `brainstorm→triage`, `brainstorm→terminal`, and that `triage` still accepts `none` (direct entry) — plus that illegal edges (e.g. `brainstorm→plan`) are blocked.
- Heartgate test: a `brainstorm→triage` transition with a conformant scope-package artifact PASSES; a missing/under-specified package BLOCKS (the exit invariant bites).
- Skill-readiness lint already covers frontmatter/`kind`; confirm `uacp-brainstorm` stays conformant after gaining writers.

## Risks / open items

- **Run-registry semantics:** decide whether a brainstorm-only run (that exits to `terminal`) registers in `run-registry.yaml` or stays a lightweight pointer. Recommendation: register it (traceable, resumable) but mark it non-advancing.
- **Bridging the old `.uacp/brainstorm/` layout** to the registered-artifact layout — a small migration in the skill body.
- **Invariant doc clarification** (above) — separate docs follow-up.
