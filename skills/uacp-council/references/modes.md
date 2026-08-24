## Modes

Mode is independent of tier. A Tier 3 council can run in brainstorm mode; a Tier 1 council can run in finding-driven mode. Mode affects **what the council looks at** and **how prompts are framed**.

### Two families of modes

**Open-ended modes** — no prior findings; the council surfaces what's true / wrong / possible:
- `review` / `audit` — produce findings with severity; return verdict.
- `correctness-screening` — the VERIFY-phase read over the kernel-produced **substrate** (the real diff from `merge-base..HEAD` + what the code did when run), charged to construct the input that defeats the work — never handed a checklist. Backs the Layer 2 correctness gate. See `[skills-root]/uacp-council/references/correctness-screening.md`.
- `triage-grounding-screening` — the TRIAGE-phase read over the real project-root slice the scope names: is the scope real, and right-sized against the actual code? Backs the TRIAGE grounding gate. See `[skills-root]/uacp-council/references/triage-grounding-screening.md`.
- `propose-grounding-screening` — the PROPOSE-phase read over the **reproduced current behavior**: is the proposal's premise *true*? Reproduce, don't read. Backs the PROPOSE grounding gate. See `[skills-root]/uacp-council/references/propose-grounding-screening.md`.
- `brainstorm` / `design` — produce competing proposals; no verdict; converge via challenge/merge/reject.
- `research` — produce evidence-backed observations with confidence and contradictions; no verdict.
- `synthesis` — Tier 3 only; the cross-runtime synthesis output mode.

**Finding-driven mode** — anchored to specific findings/concerns:
- `finding-driven` — input includes a `findings` list; the council assesses the artifact through the lens of those findings, performing up to four checks: resolution, regression, design-drift, and fix-interaction. See `[skills-root]/uacp-council/references/finding-driven-mode.md`.

### Brainstorm-mode discipline

The first round (Round 1) must receive a **minimal, non-leading packet**:
- artifact / topic scope, user goal, hard constraints, allowed mutation level, output contract
- **Exclude**: expected findings, suspected root cause, coordinator's preferred architecture, other participants' findings, desired verdict

Later rounds may introduce proposal inventories, challenges, and reconciliation packets. See `uacp-bridge` for the brainstorm output schema.