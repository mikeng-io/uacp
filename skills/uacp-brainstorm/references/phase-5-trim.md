## Phase 5: Trim Scope with the User

The purpose of brainstorming is not to expand the user's ambition — it is to help them choose a bounded slice to take into UACP.

**Conversation goal:** agree on a selected scope that is:

- Understandable in one paragraph
- Implementable without heroic effort
- Worth governing if UACP is the path
- Discardable if the user decides not to proceed

**Trimming prompts:**

> "Of the approaches we sketched, which one matches your appetite right now?"

> "If we had to cut this in half, what is the part we absolutely cannot drop?"

> "Is this something that should go through UACP governance, or is it small enough to handle informally?"

**Do not pressure the user into UACP.** If the scope is truly small and low-stakes, recommend handling it outside UACP and stop after Phase 6 (vault write).

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
