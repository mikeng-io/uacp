# UACP — Universal Agent Control Plane

Runtime-neutral governance framework for AI agent work. Lifecycle: **(optional) BRAINSTORM →** **TRIAGE → PROPOSE → PLAN → EXECUTE → VERIFY → RESOLVE**.

This file is **principles only** — the governance contract every agent must obey. All detail lives in `docs/`, the single source of truth. **Start here as an agent:** `docs/INDEX.md`.

---

## Core Principle — comprehend → measure → serialize

Machines earn reliability through **determinism**; agents are **semantic** and cannot — so they need their own discipline for trustworthy thinking. Every governed operation, *and the agent's own reasoning*, follows one invariant:

- **comprehend** — raise input to a computable model; the one semantic act, done once (do not silently re-interpret downstream);
- **measure** — reduce the model to a decidable signal that is **grounded in evidence** and **fail-closed** (PASS/FAIL/ERROR distinct) — evidence, not assertion; *determinism belongs to the verifying gate, not to the agent's judgment*;
- **serialize** — canonicalize the result into typed, provenanced state.

This is `determinism : machines :: CMS : agents` — how a semantic process earns trust without pretending to be deterministic. It is enforced two ways: **architecturally** (Guardian / Heartgate / gates / governed writers) and in the agent's **cognition** (the injected preamble, `UACP.md`). The lifecycle below is this principle iterated. Design rationale: `design/comprehend-measure-serialize/`.

---

## Authority Chain

When layers conflict, earlier layers win. An explicit entry in `docs/decisions/decision-log.md` is the only mechanism to override this order.

| Priority | Layer | Role |
|---|---|---|
| 1 | `docs/INDEX.md` | Document registry and canonical agent read order |
| 2 | `docs/` | Intent, principles, lifecycle, policy |
| 3 | `config/` | Machine-readable rules derived from docs |
| 4 | `.uacp/state/` | Current lifecycle position and run pointers |
| 5 | `skills/` (esp. `skills/uacp-state/` for state mutation contracts) | Implement the documented rules |

> **Note:** `.uacp/state/` is runtime-created — it does not exist in a fresh clone. An agent bootstrapping cold should treat a missing `.uacp/state/` as "no active run" rather than an error.

---

## Lifecycle

| Phase | Responsibility |
|---|---|
| (optional) BRAINSTORM | Pre-governance exploration; must exit to TRIAGE before any governed work begins |
| TRIAGE | Scope calibration, granularity scoring, governance routing |
| PROPOSE | Declare intent, authority, constraints, evidence obligations |
| PLAN | Produce a council-reviewed execution plan with PLAN_VALIDATION ledger entry |
| EXECUTE | Perform bounded work within Guardian policy using governed writers |
| VERIFY | Produce evidence that the plan was executed correctly |
| RESOLVE | Close the run, record lessons, release held state |

Every transition is validated by **Heartgate**. Direct phase-skipping is a blocker, not a warning. Two tracks exist (standard + goal-driven); see `docs/lifecycle/lifecycle-reference.md`.

---

## Key Invariants

These rules are non-negotiable. Violations are Heartgate blockers or Guardian blocks.

1. **TRIAGE-first** — All non-trivial work enters formal governance via TRIAGE. An optional BRAINSTORM phase may precede it (brainstorm→triage); it never skips TRIAGE.
2. **No main writes** — No active run writes directly to `main`/`master`. Use `worktree` or `branch` (see `docs/lifecycle/worktree-protocol.md`).
3. **Governed writers only** — **Governed-state writes** during a run — the `.uacp/` namespace plus lifecycle/manifest artifacts — go through governed writers, never raw filesystem writes. Use only: <!-- BEGIN GENERATED: governed-writers — derived from skills/uacp-core/scripts/tool_specs.py by scripts/gen_doc_tables.py; do not edit by hand -->`uacp_state_write`, `uacp_run_registry_update`, `uacp_escalation_event`, `uacp_artifact_write`, `uacp_entity_write`, `uacp_doc_write`, `uacp_config_write`, `uacp_contained_shell`, `uacp_gate_ledger_append`, `uacp_corpus_write`, `uacp_run_init`, `uacp_run_transition`, `uacp_run_register_artifact`, `uacp_run_finalize`, `uacp_run_abort`<!-- END GENERATED: governed-writers -->. **RELATION-plane manifest documents** (proposal, PIV/plan, execution checkpoints, assessments, resolutions, brainstorm scope-package, …) MUST be written with **`uacp_entity_write`** (typed by `kind`+`fields`; it validates, watermarks, and registers them so the graph gate sees them) — `uacp_artifact_write` rejects those kinds and is for non-manifest artifacts only. Writer-to-path mapping is documented in `docs/runtime/runtime-enforcement.md`. **Work-product writes** (project code the agent edits during EXECUTE) are **not** raw-blocked — they are contained by the worktree (Invariant #2) and captured as evidence by checkpoint/diff coverage (EXECUTE→VERIFY). See [ADR-0019](docs/architecture/0019-pretooluse-hook-narrow-scope-and-invariant-3-clarification.md).
4. **Council gate** — Any change to kernel code, policy YAML, or canonical docs requires council review before PLAN exits. Zero material findings unresolved.
5. **Evidence must be produced** — "Done" without a backing artifact and ledger entry is a Heartgate blocker. No self-attesting closures.

UACP enforces strict separation between cognitive planes — do not use Agent Council as a state database, do not let worker runtimes silently mutate phase state, do not use a Coordination Adapter to decide policy. See `docs/INDEX.md` for the planes model and skill map.

---

## Further Reading

- Full authoring contract, incl. **what belongs in `docs/`** (and what must not): `CONTRIBUTING.md`
- Canonical agent read order, skill map, and cognitive planes: `docs/INDEX.md`
- Lifecycle and tracks: `docs/lifecycle/lifecycle-reference.md`
- Proposal schema: `docs/reference/proposal-schema.md`
- Guardian + Heartgate (kernel in `skills/uacp-core/scripts/core.py`, config in `config/uacp.toml`): `docs/runtime/runtime-enforcement.md`
- Worktree isolation: `docs/lifecycle/worktree-protocol.md`
- Runtime dispatch (Codex, Claude Code): `skills/uacp-bridge/references/`
