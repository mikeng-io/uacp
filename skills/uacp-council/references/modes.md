## Modes

Mode is independent of tier. A Tier 3 council can run in brainstorm mode; a Tier 1 council can run in finding-driven mode. Mode affects **what the council looks at** and **how prompts are framed**.

### Two families of modes

**Open-ended modes** — no prior findings; the council surfaces what's true / wrong / possible:
- `review` / `audit` — produce findings with severity; return verdict.
- `brainstorm` / `design` — produce competing proposals; no verdict; converge via challenge/merge/reject.
- `research` — produce evidence-backed observations with confidence and contradictions; no verdict.
- `synthesis` — Tier 3 only; the cross-runtime synthesis output mode.

**Finding-driven mode** — anchored to specific findings/concerns:
- `finding-driven` — input includes a `findings` list; the council assesses the artifact through the lens of those findings, performing up to four checks: resolution, regression, design-drift, and fix-interaction. See `[skills-root]/uacp-council/references/finding-driven-mode.md`.

### Brainstorm-mode discipline

The first round (Round 1) must receive a **minimal, non-leading packet**:
- artifact / topic scope, user goal, hard constraints, allowed mutation level, output contract
- **Exclude**: expected findings, suspected root cause, coordinator's preferred architecture, other participants' findings, desired verdict

Later rounds may introduce proposal inventories, challenges, and reconciliation packets. See `bridge-commons` for the brainstorm output schema.