## Phase 5: Trim Scope with the User

The purpose of brainstorming is not to expand the user's ambition — it is to help them choose a bounded slice to take into UACP.

**Conversation goal:** agree on a selected scope that is:

- Understandable in one paragraph
- Implementable without heroic effort
- Worth governing if UACP is the path
- Discardable if the user decides not to proceed

A scope is *bounded enough to admit* only when it can fill the admission shape the Heartgate will check at Phase 8 — a non-empty title, description, and `in_scope`; declared side effects; a documented `authority.source`; and a `routing_advisory`. Trim toward **that shape**, not toward a feeling of smallness, so the trim is grounded in the property the gate measures rather than discovered to be short at the boundary.

**Trimming prompts:**

> "Of the approaches we sketched, which one matches your appetite right now?"

> "If we had to cut this in half, what is the part we absolutely cannot drop?"

> "Is this something that should go through UACP governance, or is it small enough to handle informally?"

**Do not pressure the user into UACP.** If the scope is truly small and low-stakes, recommend handling it outside UACP and stop after Phase 6 (vault write). Stopping is itself a recorded decision, not a silent exit — close the brainstorm run via the `aborted`-status path (the vault remains as recorded evidence). Do not leave the run silently parked at `phase: brainstorm`.

**Output of this phase:** a `selected_scope` summary agreed with the user.

```yaml
selected_scope:
  title: "What we are doing"
  description: "One-paragraph summary"
  approach_id: "A1" | "A2" | "A3"
  in_scope:
    - "..."
  out_of_scope:
    - "..."
  enter_uacp: true | false
  rationale: "Why this scope was selected"
```
