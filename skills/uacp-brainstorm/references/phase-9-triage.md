## Phase 9: Transition Forward to TRIAGE

After the brainstorm exit invariant passes (Phase 8), transition the **already-registered** brainstorm run forward to TRIAGE. The run was registered at `phase: brainstorm` on entry — do NOT `init` a new run here. There is no implicit pre-state to promote; brainstorm is a real registered phase whose sole onward edge in the codified phase graph is `brainstorm → triage`.

### Handoff protocol

Advance the existing run with the governed `uacp_run_transition` tool. This is the only crossing — you do **not** separately validate then stamp the phase. The tool *is* the boundary: it measures the brainstorm admission contract against your scope package (the forced brainstorm-exit gate inside `state_machine.handle_transition`) and, **only if that passes**, stamps `phase: triage`. The measure and the serialize are bound together in code — you request the crossing; code certifies and effects it.

```
uacp_run_transition(
  uacp_run_id        = {existing_run_id},
  from_phase         = "brainstorm",
  to_phase           = "triage",
  reason             = "brainstorm scope bounded and admissible; advancing to TRIAGE",
  authority_artifact = "brainstorm/{run_id}/07-scope-package.yaml",
  # governed-context fields (required by every governed tool):
  workspace             = {workspace},
  uacp_phase            = "brainstorm",
  policy_version        = {policy_version},
  declared_side_effects = "[]",   # string per the tool schema; the transition writes only governed state
)
```

**Results:**

- **ok** → the run is now at `phase: triage`. Proceed to TRIAGE.
- **blocked** → the response carries `blockers` naming the unmet admission-contract fields (missing/empty `title`/`description`/`in_scope`, absent `declared_side_effects`, undocumented `authority.source`, or an invalid `routing_advisory`). The phase did **not** advance. Return to Phase 5/7 to fix the scope package, then retry. Do not attempt to advance the phase by any other writer — `uacp_run_transition` is the only governed path, and the gate is fail-closed.

> Do **not** call `uacp_heartgate_check` for this crossing. That tool validates a transition *artifact* under a managed artifact/state root; the brainstorm scope package is not transition-artifact-shaped, and the admission contract is now enforced inside `uacp_run_transition` itself. The earlier "assemble an artifact + call heartgate_check + then state-write the phase" protocol was a seam in the wrong place — it asked the agent to perform a governed transform code owns, with parameters the handler never read.

### Evidence passed to TRIAGE

- `.uacp/brainstorm/{run_id}/07-scope-package.yaml` — the governed scope-package artifact
- Full session vault `.uacp/brainstorm/{run_id}/` — supporting evidence
- Heartgate findings (if any warnings were accepted)

### TRIAGE's job

TRIAGE decides:

- Does this scope deserve a full UACP lifecycle run?
- What routing depth? (`direct`, `lightweight`, `standard`, `full_governance`, `block_or_clarify`)
- Is human involvement required?
- Should a local council run before PROPOSE?

Do NOT skip TRIAGE and go directly to PROPOSE. Brainstorm produces a **candidate**; TRIAGE owns the admission decision.

### If the user declines to continue

If the user decides the scope should not advance, stop before the TRIAGE transition. The run remains at `phase: brainstorm` and the vault stays under `.uacp/brainstorm/{run_id}/` as recorded evidence. Closing a brainstorm run that will not advance uses the `aborted`-status path rather than a forward transition.
