---
name: uacp-brainstorm
description: >
  Optional UACP entry phase for exploration and scope clarification. Registers a
  formal run at phase=brainstorm, writes the scope package as a governed artifact,
  and advances brainstorm->triage via the governed transition, whose forced exit
  gate enforces the admission contract before handing off.
phase: brainstorm
kind: lifecycle
authority_source: "engines/domain/{phase_graph,phase_transitions,gate_rules}.py (phase graph + stages + gate grammar, code-authoritative; brainstorm enters_from none, only exit is triage, STAGE_ALLOWED_TOOLS[brainstorm], phase_exit_invariant brainstorm/*/07-scope-package.yaml); config/uacp.toml [heartgate.*] (operator knobs); config/phase-transitions.yaml (LLM-read adaptive-gate doctrine + artifact schemas only)"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - Write
  - uacp_state_write
  - uacp_entity_write
  - uacp_run_transition
---

# UACP Brainstorm: Optional Entry Phase

Use this skill when the user has a vague idea, ambiguous scope, or multiple possible directions. Brainstorming is an **optional formal entry phase** of the UACP lifecycle. Its job is to help the user understand what they actually want and trim it down to a bounded scope before TRIAGE.

Brainstorm is the lifecycle's **comprehend** step (see AGENTS.md Core Principle): it raises a vague idea into one bounded, gate-admissible scope — the trim (Phase 5) is the grounded reduction, and the scope package plus Heartgate (Phases 7–8) is the provenanced handoff a separate authority admits. That is why the phase order is explore → trim → serialize-to-gate rather than an arbitrary checklist.

**This skill is a governed phase.** On entry it registers a UACP run at `phase: brainstorm`, writes the scope package as a real lifecycle artifact using `uacp_entity_write`, and advances the run `brainstorm→triage` via the governed `uacp_run_transition` tool — whose forced exit gate measures the admission contract against the scope package and stamps the phase only if it passes. Brainstorm artifacts are state-persistent.

**Hard rule:** do not invoke implementation skills during brainstorming. Exploration only.

---

## Skill-Level Exploration Gate

Read: references/exploration-gate.md

---

## Quick-Start

1. Register run at `phase: brainstorm` using `uacp_state_write`.
2. Read: references/phase-1-context.md — Gather signals and classify intent
3. Read: references/phase-2-explore.md — Explore possibilities and constraints
4. Read: references/phase-3-questions.md — Ask clarifying questions one at a time
5. Read: references/phase-4-approaches.md — Sketch 2–3 candidate approaches
6. Read: references/phase-5-trim.md — Trim scope with the user
7. Read: references/phase-6-vault.md — Write rough notes to brainstorm vault
8. Read: references/phase-7-selected-scope.md — Produce the scope package (governed artifact via `uacp_entity_write`)
9. Read: references/phase-8-admission.md — Understand the brainstorm admission contract (enforced at the transition; pre-flight self-check)
10. Read: references/phase-9-triage.md — Transition to TRIAGE via `uacp_run_transition` (the crossing that measures + effects)

---

## Lifecycle Position

```text
BRAINSTORM → TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE
 ^              ^
 optional       formal UACP governance (always required for propose onward)
 entry phase
```

- Brainstorm is **optional**. A run may begin at `brainstorm`, or TRIAGE may be entered directly with no brainstorm at all (the codified `enters_from` for triage is `none | brainstorm`).
- When brainstorm IS present, its **only exit is TRIAGE** (`brainstorm` enters_from `none`; its sole onward transition in the phase graph is `brainstorm → triage`). Brainstorm never skips TRIAGE and never routes anywhere else.
- Explore-and-bail (stopping before any formal artifact) is a follow-up requiring the `aborted`-status path.
- Scope package path: `.uacp/brainstorm/{run_id}/07-scope-package.yaml` (written via `uacp_entity_write`). The codified exit-invariant glob `brainstorm/*/07-scope-package.yaml` is relative to the `.uacp/` namespace root.

---

## Notes

- **One question at a time** — never overwhelm the user with bundled questions
- **YAGNI ruthlessly** — the goal is to trim scope, not expand it
- **Explore alternatives** — always sketch 2-3 approaches before settling
- **The vault is supporting evidence** — it is raw thinking material; the scope package is the governed artifact
- **Only selected scope enters TRIAGE** — the forced exit gate inside `uacp_run_transition` checks the admission boundary
- **Anti-collapse** — one phase = one markdown file. Never merge phases.

---

## Advisory prior-art (Oracle)

**Always** call `uacp_oracle_query` early in the brainstorm phase to surface relevant
prior-art before opening the exploration vault — retrieval has a **deterministic floor**
(#100): even with the semantic Oracle disabled (the default) or its store absent,
`uacp_oracle_query` returns deterministic corpus matches over `.uacp/lessons` +
`.uacp/knowledge`. It is never silenced merely because the vector store is off.

```
uacp_oracle_query(phase=brainstorm, project=<project-id>)
```

Results are **advisory** (`trust_class=advisory`, `evidence_required=true`). Use them
to seed the vault and inform scope calibration — never treat them as authoritative.
If `uacp_oracle_query` returns no packets (an empty corpus), proceed without retrieval.
