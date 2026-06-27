# Contributing to UACP

This document defines the authoring contract for UACP changes. Everything that touches the kernel, policy YAML, canonical docs, or runtime adapter source goes through the UACP lifecycle itself (UACP eats its own dogfood).

## Before you start

1. Read [PROJECT.md](PROJECT.md) for what UACP is and its current state.
2. Read [`docs/policy/constitution.md`](docs/policy/constitution.md) for the non-waivable invariants.
3. Read [`docs/policy/first-principles.md`](docs/policy/first-principles.md) for the reasoning principles UACP enforces.

## Authoring a change

### 1. Open a run via TRIAGE

Create `proposals/{run_id}-triage.yaml` describing the request. TRIAGE routes to one of:

| Route | When to use |
|---|---|
| `direct` | Trivial work (typo fix, single-line doc edit). Bypasses the full lifecycle. |
| `lightweight` | Bounded operational change (e.g. update a config value). |
| `standard` | Full lifecycle with adaptive evidence selection. |
| `full_governance` | Architectural change. Requires multi-phase plan + council review per phase. |
| `block_or_clarify` | Authority unclear or scope exceeds operator authorization. |

See [`docs/reference/proposal-schema.md`](docs/reference/proposal-schema.md) for the canonical artifact schema.

### 2. Author the proposal (`uacp-propose`)

Required:
- `authority.requested_by` and `authority.authorization_source` (verbatim or citation).
- `scope.in_scope` non-empty.
- `declared_side_effects` itemized by kind (file_write / state_mutation / git_commit / api_call / publication / irreversible_write / runtime_surface).
- `viability.assessment` ∈ {viable, not_viable, needs_revision}.

### 3. Plan, with PLAN_VALIDATION (`uacp-plan`)

Required artifacts:
- `plans/{run_id}-plan.yaml` and `plans/{run_id}-scope.yaml`.
- Append a `PLAN_VALIDATION` ledger record via `uacp_gate_ledger_append` covering all six pv_ids (`pv_1`..`pv_6`) with explicit per-check pass evidence (mapping-form OR sibling `check_results`). Heartgate blocks PLAN→EXECUTE otherwise. See [`docs/reference/skill-enforcement-spec.md`](docs/reference/skill-enforcement-spec.md) for the contract.

Run-registry registration:
- The codified `run_registry_rule` (`engines/domain/gate_rules.py` `run_registry_rule_default()`, Slice 4b; `required_for_transition: plan->execute`) declares the registry is consulted at every PLAN→EXECUTE in every mode. Any two concurrent runs whose `scope.write_paths` overlap will mutually block unless both register.
- Manual-mode runs MAY skip registration when operator-driven serialization is the compensating control (no concurrent UACP run is open). Heartgate's overlap check then has nothing to flag.
- `supervised_auto` / `full_auto` mode runs (Phase 5+) MUST register via `uacp_run_registry_update` op=register after PLAN_VALIDATION and deregister at RESOLVE. `config/uacp.toml [autonomy] modes.{supervised_auto,full_auto}.run_registry_registration_required: true` documents this obligation (kernel reader lands in Phase 5).

### 4. Execute (`uacp-execute`)

- All writes must fall within `scope.write_paths` declared in the scope artifact.
- Use governed writers (`uacp_state_write`, `uacp_artifact_write`, `uacp_doc_write`, `uacp_config_write`, `uacp_gate_ledger_append`, `uacp_run_registry_update`, `uacp_escalation_event`) — never raw filesystem writes through generic tools.
- For shell/code execution: `uacp_contained_shell` with bwrap attestation, NOT `terminal` / `execute_code` (those are deliberately Layer-B-forbidden in most phases).

### 5. Verify (`uacp-verify`)

- For each non-deferred, non-not_applicable cluster, produce a `verification/{run_id}-{cluster}-verified-facts.md` + `verification/{run_id}-{cluster}-assumptions.md` pair.
- Assumptions table must use the canonical header (`| Assumption | Disposition | Owner | Next-phase obligation |`).
- Any `pending` disposition needs a non-empty Owner AND Next-phase obligation.
- **Self-approval guard**: VERIFY must not remediate its own material findings and then self-certify final closure. If material findings surface during VERIFY, route to PLAN or EXECUTE for remediation, then re-enter VERIFY.

### 6. Resolve (`uacp-resolve`)

- Emit `.outputs/{run_id}-lessons.yaml` matching the `lessons` schema in `engines/domain/artifact_schema.py` (`artifact_schemas_dict()`; `config/artifact-schemas.yaml` deleted Slice 5). Include `ledger_citations` for non-trivial lessons.
- Update `state/current.yaml` to `active_status: resolved`. Note: `state/current.yaml` is caller-bound — the new content's `active_run_id` must match the caller's `uacp_run_id`. Bootstrap-mode writes (file absent) are permitted to seed.

## Council review gate

Every phase that changes the kernel, policy YAML, or canonical docs is gated by a Codex council review (technical + governance + skeptic, parallel). The pass-only threshold is **zero material findings unresolved**. Two-pass minimum; three-pass for phases introducing a new enforcement category.

Per-phase reviews are recorded under `verification/{run_id}-phaseN-codex-review.yaml`. The global cross-phase audit (after RESOLVE) goes to `verification/{run_id}-global-review.yaml`.

## Code conventions

### Kernel changes (`runtime-adapters/hermes/plugins/uacp_guardian/`)

- Every new authority list **must** live in `config/` YAML, not kernel code. The hidden-authority anti-pattern is the original sin we're guarding against.
- Every new governed writer **must** call `_required_uacp_context_missing` (or `_validate_common_write_args`) at handler entry.
- Every fail-closed validator branch **must** have a paired check in the phase verify script. Coverage-by-symmetry is insufficient.
- Path comparisons **must** use `_canon_write_path` / `_paths_overlap` (PurePosixPath segment normalization), not raw string startswith.
- YAML fields that LOOK like enforcement but have no kernel reader **must** carry `enforcement_status: stub_only_phase_N` or the `_advisory` suffix.

### Documentation — what belongs in `docs/` (and what does not)

`docs/` is the **canonical, runtime-neutral governance authority** (Authority-Chain
layer 2): *normative* prose only — intent, principles, the lifecycle model,
doctrine, architecture decisions, canonical schemas, and curated reading guides.
Every file carries OKF frontmatter with `type ∈ {adr, policy, spec, reference,
guide, plan, design, decision}`. Do not add files to `docs/` outside this scope.

**Belongs in `docs/`:**

| Subdir | Holds |
|---|---|
| `policy/` | Non-waivable doctrine, first principles, alignment spec |
| `lifecycle/` | Phase model, transitions, verification & review model |
| `runtime/` | Runtime-**neutral, normative** enforcement contracts (the spec *every* adapter must satisfy) |
| `reference/` | Canonical schemas & specs (proposal schema, skill-enforcement spec, …) |
| `architecture/` | ADRs (numbered, with template) |
| `decisions/` | Operational decision log (continuous) |
| `guides/` | Curated human/agent reading paths synthesizing the above |
| `plans/`, `archived/` | Forward plans / reserved slots; superseded docs |

**Does NOT belong in `docs/` → correct home:**

| Kind | Goes to |
|---|---|
| Runtime/adapter-**specific** how-to (install steps, per-runtime dispatch, hook wiring, MCP setup) | `runtime-adapters/<x>/README.md` or `skills/uacp-bridge/references/` |
| Skill-specific contracts/usage | the skill's `SKILL.md` + `skills/<skill>/references/`; shared kernel contracts → `skills/uacp-core/references/` |
| Lesson/knowledge **corpus** | `.uacp/knowledge/` + `.uacp/lessons/` (Oracle-owned; different OKF vocab) |
| Code/module READMEs | co-located with the code |
| Project orientation (front door, identity, roadmap) | root `README.md` / `PROJECT.md` / `ROADMAP.md` |
| Run artifacts, generated content, indexes, fixtures | `.uacp/…` (gitignored), `tests/` |

**The neutral-vs-specific line for runtime material:** a runtime-**neutral
normative contract** (what *all* adapters must do) lives in `docs/runtime/`; a
runtime-**specific operational how-to** (how to install/wire Claude Code or Kimi)
lives *with the adapter* (`runtime-adapters/`), never in `docs/`.

The allowed `docs/` subdir set and the `type` vocab are mechanically enforced by
`tests/unit/test_docs_okf.py`; the neutral-vs-specific content judgment is a
human/agent rule.

### Tests

- Each phase has a `scripts/phaseN_verify.py` script. Every new fail-closed branch needs a paired check.
- For governed writer changes, also run `scripts/live_guardian_probe.py` and confirm no NEW failures (4 pre-existing failures documented as pc_7 / pc_8).

## Commit conventions

- Atomic per phase: one commit per phase + one per remediation cycle.
- Commit message format: `<type>(<scope>): <subject>` (e.g. `feat(heartgate): Phase 3 — plan_validation_gate, run_registry, authority docs`).
- Co-author trailers are preserved.
- Never amend a pushed commit; create a follow-up commit.

## Pull request conventions

- Title, `type:` label, assignee, and branch name (`<type>/description`) are **hard-gated** by the PR Policy workflow.
- PR body: GitHub auto-loads `.github/pull_request_template.md` (a scaffold, not gated). Fill `## What` and `## Verified` on every PR; add `## Review` when the change touches kernel, policy YAML, or canonical docs (Invariant #4); add `## Links` / `## Deferred` when relevant. Delete the rest.

## What requires operator authorization (not contributor-self-authorized)

The list below distinguishes **mechanically enforced** (kernel refuses; no operator override possible without explicit policy change) from **authoring contract** (no kernel enforcement today; the rule is documentation-only and depends on contributor discipline).

**Mechanically enforced** (kernel rejects):
- Modifying `state/current.yaml` outside a governed UACP run — `uacp_state_write` caller-binds writes to this path (kernel: `runtime-adapters/hermes/plugins/uacp_guardian/__init__.py#_handle_uacp_state_write`).
- Writing under `state/gate-ledger/` via anything other than `uacp_gate_ledger_append` — refused at the handler.
- Writing `state/run-registry.yaml` via anything other than `uacp_run_registry_update` — refused at the handler.
- Writing under `state/escalations/` via anything other than `uacp_escalation_event` — refused at the handler.

**Authoring contract** (documentation-only; no kernel reader yet):
- Opening Phase 5 (or any future reserved_slot phase). Phase 5 prerequisites in `docs/plans/phase5-reserved-slot.md` are doc-level — a mechanical pre-check is on the Phase 5 backlog (`pc_g_skep_007`).
- Force-pushing to `main`. There is no git hook in this repo; the rule is contributor discipline.
- Authoring a proposal with `blast_radius` ∈ {high, critical}. `config/uacp.toml [autonomy.escalation_triggers] trigger_blast_radius_high` describes the intended trigger, but the kernel reader for this is Phase 5.
- Decisions that supersede an `accepted` ADR (must propose a new ADR superseding the old one, not edit in place).

## Cross-references

- Build/test commands: [COMMANDS.md](COMMANDS.md).
- Roadmap and reserved phases: [ROADMAP.md](ROADMAP.md).
- ADR template: [`docs/architecture/0000-template.md`](docs/architecture/0000-template.md).
