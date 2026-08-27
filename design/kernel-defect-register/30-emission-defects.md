---
type: analysis
title: Emission defects — what the kernel computes and never tells the agent
description: D-09 to D-13. The kernel derives structured diagnostics, phase contracts, and preconditions, then ships strings.
tags: [emission, ergonomics, tooling, state]
timestamp: 2026-08-22
edges:
  - {dst: 00-register, rel: depends_on, provenance: derived}
  - {dst: 20-grounding-defects, rel: extends, provenance: asserted}
---

# Emission defects

The unifying claim of this node: **UACP's agent-facing surface is narrower than its internal
model, everywhere, and the loss is at the boundary rather than in the computation.**

## D-09 — Structured diagnostics are computed, then flattened away · VERIFIED

`engines/base.py:24` defines the engine result type with a field documented as
*"optional structured context for programmatic consumers"*:

```python
detail: dict = field(default_factory=dict)
```

Every emission site discards it:

| Site | Code |
|---|---|
| `state_machine.py:523` | `blockers = [f"{v.code}: {v.message}" for v in violations if v.severity == "block"]` |
| `state_machine.py:524` | `advisories = [f"{v.code}: {v.message}" …]` |
| `heartgate/heartgate.py:651` | `line = f"{v.code}: {v.message}"` |
| `heartgate/heartgate.py:804` | `blockers.append(f"{v.code}: {v.message}")` |

There are no programmatic consumers because the boundary makes them impossible. The agent
receives a flat list of strings with no per-gate attribution, no severity structure beyond the
block/advisory split, no offending path, and no remedy field — for findings the engine knew all
of that about.

## D-10 — No read-side state tool · VERIFIED

Eighteen tools are registered in `tool_specs.py`. Fifteen are writers; three are `read_only`
(`uacp_sandbox_check`, `uacp_heartgate_check`, `uacp_oracle_query`). None reads run state.

`handle_read` exists in `state_machine.py` — *"Read an existing run manifest"* — and is **not
registered in `tool_specs.py`**. Its only callers are tests.

A returning agent therefore has no governed way to ask *where am I, what have I already done*.
It must `cat` files it has not been told exist. Combined with D-11, its documented alternative
is wrong.

## D-11 — The documented re-orientation reads fields nothing writes · VERIFIED

`skills/uacp-context/references/uacp-state-integration.md:3-21` instructs the agent to
`cat .uacp/state/current.yaml` and merge:

```yaml
current_phase: ""         # triage | propose | plan | execute | verify | resolve
pending_transitions: []
recent_artifacts: []
blockers: []
```

`CurrentPointer` (`engines/domain/pointer.py`) carries `active_run_id` and
`active_run_manifest`. That is all. Four of the five fields the skill names are never written by
anything.

The fifth problem is the pointer itself: `handle_init` writes it **only if it does not already
exist**, and `handle_transition` never touches it. So it is a create-once pointer, not a live
cursor — stale from the first phase crossing, and wrong outright if a second run starts.

The authoritative record is the run manifest (`status`, `current_phase`, `state_history`,
`artifacts`). The skill points the agent at the one file that is not it.

## D-12 — MCP ships the label, not the contract · VERIFIED

`tool_specs.py` gives every `ToolSpec` two description fields: `description` (a short
register_tool label) and `schema_description` (the JSON-schema-level text carrying
preconditions — what the tool validates, what it refuses, what must be true first).

`runtime-adapters/mcp/uacp_mcp_server.py:66`:

```python
description=spec.description,
```

So an MCP client sees *"Governed UACP state writer"* rather than the sentence explaining the
governed state-mutation boundary. The instructive text exists, is substantially larger, and is
never shipped to the runtime that most needs it.

## D-13 — No forward guidance at a crossing, though the data exists · VERIFIED

`uacp_run_transition` returns, on success:

```python
{"ok": True, "run_id": run_id, "from_phase": from_phase, "to_phase": to_phase}
```

plus `advisories` when graph findings are non-blocking, plus a rework block. The sole instance
of the kernel telling an agent what to do next anywhere in the codebase is `rework_briefing`
(`state_machine.py:818-827`) — emitted only on EXECUTE entry, only for a rework run with
carried findings.

Every `next_phase_*` symbol in the kernel is a field the agent must **fill in**:
`next_phase_obligation`, `next_phase_readiness`, `next_phase_acceptance`, `next_phase_handoff`
(`engines/domain/schema.py:505,545`; `deferral_completeness.py:103`;
`heartgate/validators/coherence.py:58`). UACP collects forward obligations exhaustively and
replays none of them.

**The data for the fix is already sitting in the repo.** `stages_default()`
(`engines/domain/phase_transitions.py`) holds `enters_from`, `exits_to`, `purpose`,
`allowed_tools`, and `phase_exit_invariants` per phase, and Heartgate loads it at construction.
`config/state.yaml` `lifecycle_skill_contracts` maps every phase to its owning skill,
responsibility, and write scope. A `next` block naming the required skill, the phase purpose,
what the next crossing will be gated on, and the obligations the previous phase recorded is a
join over data the kernel already holds — not new modelling.
