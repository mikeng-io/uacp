---
name: uacp-brainstorm
description: >
  Optional UACP entry phase for exploration and scope clarification. Registers a
  formal run at phase=brainstorm, writes the scope package as a governed artifact,
  and runs Heartgate to validate brainstorm->triage admission before handing off.
kind: orchestration
location: managed
dependencies:
  - uacp-context
  - domain-registry
  - uacp-bridge
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(ls *)
  - Bash(git log *)
  - Bash(git diff *)
  - Task
  - Write
  - Bash(mkdir *)
  - uacp_state_write
  - uacp_artifact_write
  - uacp_heartgate_check
---

# UACP Brainstorm: Optional Entry Phase

Use this skill when the user has a vague idea, ambiguous scope, or multiple possible directions. Brainstorming is an **optional formal entry phase** of the UACP lifecycle. Its job is to help the user understand what they actually want and trim it down to a bounded scope before TRIAGE.

**This skill is a governed phase.** On entry it registers a UACP run at `phase: brainstorm` using `uacp_state_write`, writes the scope package as a real lifecycle artifact using `uacp_artifact_write`, and runs `uacp_heartgate_check` for the `brainstorm→triage` transition before handing off. Brainstorm artifacts are state-persistent.

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
8. Read: references/phase-7-selected-scope.md — Produce the scope package (governed artifact via `uacp_artifact_write`)
9. Read: references/phase-8-admission.md — Run `uacp_heartgate_check` for brainstorm→triage
10. Read: references/phase-9-triage.md — Transition to TRIAGE (`uacp_heartgate_check` transition)

---

## Lifecycle Position

```text
BRAINSTORM → TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE
 ^              ^
 optional       formal UACP governance (always required for propose onward)
 entry phase
```

- A run may begin at `brainstorm` (optional) or at `triage` (direct entry).
- Brainstorm **always precedes** TRIAGE — it never skips it.
- `brainstorm → triage` is the only exit in this slice. Explore-and-bail (stopping before any formal artifact) is a follow-up requiring the `aborted`-status path.
- Scope package path: `.uacp/brainstorm/{session_id}/07-scope-package.yaml` (registered via `uacp_artifact_write`).

---

## Notes

- **One question at a time** — never overwhelm the user with bundled questions
- **YAGNI ruthlessly** — the goal is to trim scope, not expand it
- **Explore alternatives** — always sketch 2-3 approaches before settling
- **The vault is supporting evidence** — it is raw thinking material; the scope package is the governed artifact
- **Only selected scope enters TRIAGE** — Heartgate checks the admission boundary

---

## Advisory prior-art (Oracle)

When the Oracle engine is enabled (`oracle.enabled=true` in `.uacp/config.toml`), call
`uacp_oracle_query` early in the brainstorm phase to surface relevant prior-art before
opening the exploration vault.

```
uacp_oracle_query(phase=brainstorm, project=<project-id>)
```

Results are **advisory** (`trust_class=advisory`, `evidence_required=true`). Use them
to seed the vault and inform scope calibration — never treat them as authoritative.
If oracle is disabled or returns no packets, proceed without retrieval.
- **Anti-collapse** — one phase = one markdown file. Never merge phases.
