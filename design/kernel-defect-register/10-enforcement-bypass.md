---
type: analysis
title: Enforcement bypass — gates that can be crossed without meeting them
description: D-01 to D-03. Two gate ladders, an ungated first crossing, and a Guardian that never sees a dispatch.
tags: [heartgate, guardian, transitions, bypass]
timestamp: 2026-08-22
edges:
  - {dst: 00-register, rel: depends_on, provenance: derived}
---

# Enforcement bypass

## D-01 — Two gate ladders, and the live one does not know about the other · VERIFIED

`uacp_heartgate_check` is registered `read_only=True` (`skills/uacp-core/scripts/tool_specs.py`,
the `uacp_heartgate_check` spec). Its `HeartgateDecision` is returned to the agent and consumed
by nobody: `_handle_transition_locked` in `skills/uacp-state/scripts/state_machine.py` never
calls `Heartgate.validate_transition` and never checks whether the agent ran it.

So two gate sets exist. The **advisory** set (`validate_transition`, ~20 validators, plus the
`phase_exit_invariants` table at `engines/domain/phase_transitions.py:217-292`) is what an agent
sees when it asks. The **live** set is what actually gates `uacp_run_transition`.

**This is known and partially closed.** The `forced_*` family exists precisely to push specific
Heartgate checks onto the live path (#99), and `state_machine.py` says so in its own comments —
`:713` *"…just because the agent skipped `uacp_heartgate_check`. Fail-closed."*, `:718` *"the
governed transition tool bypasses"*, `:554` *"skip `validate_transition`, and advance via
`handle_transition`"*. Currently forced: brainstorm admission, proposal coverage, execute
evidence, verify evidence, and plan-exit ×3.

**What remains uncovered:** the `phase_exit_invariants` beyond the forced set, the adaptive
package gates, and the PPV gate. The defect is not "Heartgate does not gate" — it is that the
retrofit is incomplete and there is no invariant asserting the two ladders agree.

## D-02 — The first crossing is ungated · VERIFIED

`_GRAPH_GATED_PHASES: frozenset[str] = frozenset({"plan", "execute", "verify"})`
(`state_machine.py:494`). `triage` is not a member, and no `forced_*` gate self-gates to it. So
`triage → propose` crosses the live path with **zero** structural gates — while the same handler
still auto-emits the `TRIAGE->PROPOSE` and `TRIAGE_COMPLETE` ledger records.

The consequence is specific: the ledger afterwards is indistinguishable from one where a gate
passed. The record of a gate exists; the gate does not. Every downstream coherence check that
reads the ledger for `TRIAGE_COMPLETE` (`engines/coherence.py`,
`heartgate/validators/phase_exit.py`) treats that as satisfied evidence.

This matters more than its position suggests: TRIAGE is where scope, granularity, and routing
are set — the classification every later gate keys off (`config/gate-selection.yaml`
`classification_inputs`). The one crossing that decides how hard everything downstream will be
checked is itself the one crossing that is not checked.

## D-03 — The Guardian never sees a dispatch · VERIFIED

`runtime-adapters/shared/guardian_pretooluse.py:66`:

```python
_RAW_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
```

and `:189`: `if tool_name not in _RAW_WRITE_TOOLS: return 0`. Every other tool call exits before
any policy evaluation. `Task` appears **nowhere** in `config/uacp.toml` — it is not classified
under `[guardian.host_tool_classification.claude_code]` at all.

Meanwhile `STAGE_ALLOWED_TOOLS` (`engines/domain/phase_transitions.py:88-105`) lists `Task` for
`brainstorm` and for no other phase, under a comment declaring it *"consumed by Guardian Layer-B
(all phases)"*. Read as documentation, that is a per-phase dispatch policy: agents may fan out
during brainstorm and nowhere else. Read as code, it is inert — the tool call never reaches
`evaluate()`, because the hook returned 0 four steps earlier.

The gap between those two readings is the defect. An operator auditing
`phase_transitions.py` would conclude dispatch is governed per-phase. It is ungoverned in every
phase.
