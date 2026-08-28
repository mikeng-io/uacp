---
type: decision
title: Remediation — four architectural moves, not eighteen patches
description: WHERE each fix lands and HOW, grouped by root cause rather than by defect. Sequenced by what unlocks what.
tags: [remediation, architecture, sequencing]
timestamp: 2026-08-24
edges:
  - {dst: 10-enforcement-bypass, rel: decides_on, provenance: asserted}
  - {dst: 20-grounding-defects, rel: decides_on, provenance: asserted}
  - {dst: 30-emission-defects, rel: decides_on, provenance: asserted}
  - {dst: 40-operational-reality, rel: decides_on, provenance: asserted}
---

# Remediation

Eighteen defects, four root causes. Patching them one by one would re-create them one by one —
each is a symptom of a missing structure, and the structure is what should be built.

---

## M0 — Enable the plugin here (prerequisite, not a fix) · D-14

**Where:** `.claude/settings.local.json` / the user's `enabledPlugins`.

**Why first:** UACP is developed in an environment where UACP is off. Every fix below is
unverifiable until the SessionStart injection, the Guardian hook, and the governed writers are
actually live in this repo. This is also the causal mechanism behind the register's recurring
pattern — *the mandate is never felt during development*, so shipping the tooling without the
mandate reads as complete.

**How to know it worked:** run one governed transition and confirm the Guardian denial fires on
a raw `.uacp/` write. If it does not, nothing below can be trusted.

---

## M1 — One gate resolver · D-01, D-02

**The root cause is duplication, not omission.** The live gate set is assembled by a hand-
maintained `+=` chain at `skills/uacp-state/scripts/state_machine.py:719-734`; the advisory set
lives in `Heartgate.validate_transition`. Adding a gate means remembering two places. D-01 is
exactly that memory failing, and the `forced_*` family is the manual repair.

**Where:** extract a single resolver — `resolve_gates(from_phase, to_phase, track,
routing_outcome) -> GateSet` — and have **both** `_handle_transition_locked` and
`validate_transition` call it. The `forced_*` functions become rows in that resolver's table
rather than a chain of `+=` calls.

**How this kills D-02:** `_GRAPH_GATED_PHASES = {"plan","execute","verify"}` stops being a
separate hardcoded frozenset. `triage → propose` gets whatever the resolver says it gets, and
the answer becomes a policy decision recorded in one place instead of an absence nobody notices.

**The invariant that makes it stay fixed:** a test that, for every legal `(from,to)` pair,
asserts the live gate set equals the advisory gate set. That test failing *is* the defect —
it can no longer be re-introduced silently.

**Cost:** kernel code → Invariant #4, council review before PLAN exits. This is the most
structural of the four and the one to do carefully, not quickly.

---

## M2 — An evidence-reference type · D-04

**Cheapest, highest value, and the code already exists ten lines away.**

**Where:** `skills/uacp-core/scripts/engines/rework_completeness.py:261`. It currently returns
`bool(_str_field(entry, "handling_artifact_path"))`. The function already receives `root`
(`_max_rework_depth(root)`, `_collect_dispositions(root, manifest)`), and
`scripts/validate_uacp_artifacts.py` already defines `_artifact_exists(root, artifact)` (`:573`)
and `_artifact_run_bound(artifact, run_id)` (`:588`) — both already applied to
`accepted_exceptions[].artifact_path` at `:271-276`.

**How, architecturally:** do not patch the one field. Introduce the **type**. Any field that
names an artifact *as proof* resolves through one checker:

| Check | Source |
|---|---|
| exists on disk | `_artifact_exists` |
| run-bound | `_artifact_run_bound` |
| path-prefix legal (`verification/` \| `resolutions/` \| `executions/`) | existing prefix rule |
| hash-registered, where a watermark exists | `state/hashes/{run}.json` |

Then the rule is stateable and general: **a claim of the form "X is proven by Y" never validates
on Y's presence, only on Y's resolution.** Apply it to `handling_artifact_path` first, then
sweep every other evidence-bearing field for the same shape.

**Proof it worked:** a negative fixture — a `remediated` entry naming a nonexistent path must
BLOCK. Today it passes. That fixture is the regression guard for the entire class.

---

## M3 — Ground the planes that already exist · D-05, D-06, D-07, D-08

Three separate changes, one principle: **stop letting the agent elect whether reality is
consulted.**

**(a) The floor must key off the work, not the declaration.** `projection.py:481` returns `[]`
when a run has no check nodes, and `validate_check_floor` iterates only classes the agent
declared. So the agent chooses the question it will be graded on. Invert it: derive the required
plane from the *work_unit's* intent/class, and fail a run whose work implies a behavioral or
symbol claim but carries no check of that kind. The class→required-kind table in
`config/verification-floor.yaml` is the right place; what changes is that the floor is applied
to inferred classes, not only declared ones.

**(b) Make the code plane reachable.** `build_code_index` has no production caller, so
`code_plane`'s ERROR-on-missing-index is a block nobody ever hits because nobody ever gets that
far. Give it one caller — at PLAN exit, or lazily on the first `symbol_resolves` need — so the
plane is a working gate rather than an aspiration.

**(c) Promote the one independent witness.** `SC_DIFF_OUT_OF_SCOPE`
(`scope_conformance.py:526`) should **block** when the run declared `write_paths` — fail-closed
on the agent's own declaration, which is the least arguable form of the rule. Keep
`SC_DIFF_UNAVAILABLE` (`:513`) at warn: an unobservable repo is an environment fact, not an
agent fault.

**Migration, because (c) will break live runs:** ship behind a config key with warn as the
current default, flip the default in a named release, and keep the escape as an explicit,
greppable opt-out — the same asymmetric pattern `config/phase-transitions.yaml` already
documents for codified gates.

**(d) Give the rework cap a breaker · D-08.** `RW_REWORK_DEPTH_ESCALATION` warns at
`max_rework_depth` (5). UACP already has the pattern built: `heartgate/validators/ppv.py:202-211`
pairs `max_attempts` with `second_failure_action = block_unconditional`. Apply that grammar to
the rework loop — at the cap, require an adjudication record per open finding (what was decided,
why, what it costs if wrong) and block without it. Cap without a defined trip action is a
counter, not a gate.

---

## M4 — One response envelope · D-09, D-10, D-11, D-12, D-13

**The root cause is that there is no agent-facing response contract** — there are eighteen
ad-hoc dicts. Define one, and five defects close together.

**Where:** every governed handler's return in `skills/uacp-state/scripts/`, plus
`engines/base.py` (the `Violation` type) and `runtime-adapters/mcp/uacp_mcp_server.py:66`.

**The envelope:** `{ok, state, findings[], next}`

- **`findings[]`** carries `code · severity · message · detail · path` — stop flattening to
  `f"{v.code}: {v.message}"` at the four sites in `state_machine.py:523-524` and
  `heartgate.py:651,804`. `Violation.detail` is already documented as *"structured context for
  programmatic consumers"*; there are no consumers because the boundary destroys it. **(D-09)**
- **`next`** is a **join over data the kernel already holds** — not new modelling:

  | Field | Source |
  |---|---|
  | `required_skill` | `config/state.yaml` `lifecycle_skill_contracts.skills` |
  | `phase_purpose`, `write_scope` | same, plus `stages_default()` `purpose` |
  | `will_be_gated_on` | M1's resolver, asked for the *next* crossing |
  | `carried_obligations` | the previous phase's recorded `next_phase_obligation` entries, replayed |

  `rework_briefing` (`state_machine.py:818-827`) is the working precedent: generalize it from
  one special case to every crossing. **(D-13)**
- **Register `handle_read`** as `uacp_run_status`, returning the same envelope. It exists in
  `state_machine.py` and is absent from `tool_specs.py`; today a returning agent has no governed
  way to ask where it is. **(D-10)**
- **Delete the wrong fields** from `skills/uacp-context/references/uacp-state-integration.md` —
  `current_phase`, `pending_transitions`, `recent_artifacts`, `blockers` are not written by
  anything — and point re-orientation at the run manifest, which is authoritative. **(D-11)**
- **`uacp_mcp_server.py:66`**: ship `spec.schema_description`, not `spec.description`. One line;
  it is the difference between a 4-word label and the tool's preconditions. **(D-12)**

**Why this is one move and not five:** each of those five is the same boundary. Fixing them
separately means five negotiations about response shape; fixing the contract once means the
next handler cannot re-create the problem.

---

## M6 — D-03: split it, park one half, fix the other · D-03

D-03 (the Guardian never sees a dispatch) had no owner in the first draft of this node — the
register promised eighteen defects grouped by root cause and left one enforcement bypass
without a remedy. It is two defects wearing one number, and they have different fates:

- **Coverage half — parked.** Extending `_RAW_WRITE_TOOLS` (or the host-tool classification) so
  the Guardian evaluates `Task` is gate-building. It parks with the lane per
  `70-verify-non-convergence.md`; reviving it means arguing that a dispatch gate would have
  caught something a reader would not.
- **Coherence half — not parked, and cheap.** `STAGE_ALLOWED_TOOLS` lists `Task` for
  `brainstorm` and no other phase, under a comment declaring it *"consumed by Guardian Layer-B
  (all phases)"*. An operator reading `phase_transitions.py` concludes dispatch is governed
  per-phase; it is ungoverned in every phase. That gap between what the table says and what
  runs is a documentation defect independent of whether the gate is ever built — fix it by
  annotating the entry as inert-pending-coverage, or by removing the `Task` row so the table
  stops describing a policy that does not exist.

The second half is the one worth doing now: a table that lies about enforcement is worse than a
table that does not mention it, and it costs a comment.

## M5 — Operational · D-15, D-16, D-17, D-18

- **D-16 — hand dispatches file paths, not pasted text.** Change `uacp-parallel`'s task schema
  from `prompt: <text>` to `brief: <path>`, add the brief-writer that extracts a work_unit's
  text to a file, and do the same for council/bridge dispatch. At ~405 invocations for a
  `full_governance` run, coordinator-context cost is not a detail. Exactly one path (the debate
  coordinator's `round-{k}/` pointers) already does this — extend the pattern it proves.
- **D-17 — call the independence scripts from the kernel.** `review_sandbox.sh` and
  `check_model_authorized.py` are built, tested, and invoked by nothing; `read_only_enforcement`
  and `model_authorized` arrive as self-declared report fields. Make the synthesis validator
  require the scripts' exit evidence rather than the agent's word — same principle as M2.
- **D-18 — relocate the router accretion.** Move the incident-derived sections out of
  `skills/uacp/SKILL.md` and into the skill that owns each decision, in decision-point form
  (a condition and its consequence) rather than narrative. The knowledge is real; the shape and
  the location are wrong.
- **D-15 — per-runtime cognition** stays open: it needs a session-start equivalent per adapter,
  and until then cross-runtime reviewers work without the preamble.

---

## Sequence

1. **M0** — enable the plugin. Nothing below is verifiable without it.
2. **M2** — evidence-reference type. Smallest diff, largest integrity gain, helpers already
   written, negative fixture is trivial.
3. **M4** — the response envelope. Big ergonomic win, no semantic risk, closes five defects.
4. **M1** — the gate resolver. Structural, council-gated, needs the equality invariant test.
5. **M3** — grounding promotions. Real semantic risk; needs the migration window.
6. **M5** — operational, in parallel with the above.
7. **M6** — the coherence half is a comment and can land any time; the coverage half parks.

## What this does not fix

None of these makes verification *read the work for undeclared defects*. M2 and M3 raise the
floor from "the agent said so" to "the artifact resolves and the declared planes were actually
run" — that is conformance grounded in reality, which is strictly better than conformance
grounded in assertion, and still not correctness review. That gap is a separate design problem
and belongs with `design/grounded-governance/`, not here.

---

## Status / Checkpoint

**2026-08-27** — verified against `main` at this bundle's merge. Much of this node shipped while
it was open, via the `feat/verify-grounding` lane (#173) and the mcp-pin work (#175):

| Move | State | As-built |
|---|---|---|
| **M0** — enable the plugin here | **OPEN** | `enabledPlugins` still carries no `uacp` entry; the enforcement surface is still inert in its own dev environment |
| **M1** — one gate resolver | **BUILT** | `state_machine.resolve_gates(from_phase, to_phase)`; the hand-maintained `+=` chain is gone |
| **M2** — evidence-reference type | **BUILT** | `rework_completeness._artifact_resolves` — with a *stronger* run-binding than this node proposed: `_run_bound_under` requires a real delimiter after the run id and rejects `..`, so a run cannot discharge via a different run whose id merely shares its prefix |
| **M3(a)** inferred-class floor | **PARKED** | gate-building; parks with the lane (node 70) |
| **M3(b)** `build_code_index` caller | **PARKED** | same |
| **M3(c)** promote the git witness | **BUILT** | `SC_DIFF_OUT_OF_SCOPE` is now `severity="block"` — and node 70 records that it *still* does not catch P1 |
| **M3(d)** rework-cap breaker | OPEN | `RW_REWORK_DEPTH_ESCALATION` still warns at the cap |
| **M4** — one response envelope | **BUILT** (partly) | the `next` block is emitted; `uacp_run_status` is registered (D-10); MCP ships `spec.schema_description` (D-12); the phantom `current.yaml` fields are gone from `uacp-context` (D-11). `Violation.detail` (D-09) still flattens |
| **M5** — operational | OPEN | dispatch still passes prose rather than file paths |
| **M6** — D-03 split | OPEN | the Guardian still does not see `Task` |

**Read this before treating any move above as work still to do.** The register (00–40) describes
the state at audit time; this table is where it stands now.
