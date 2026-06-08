## Phase 3: Domain & Prompt Planning

Read domain definitions from `domain-registry`:

```
Read: [skills-root]/domain-registry/domains/technical.md
Read: [skills-root]/domain-registry/domains/business.md
Read: [skills-root]/domain-registry/domains/creative.md
```

For each domain in `council_manifest.domains`, resolve:
- `expert_role` — domain-registry's named expert
- `focus_areas` — what the expert should focus on
- `standards` — what standards or references apply

These flow into every sub-agent / runtime adapter prompt. **Mode matters:** for `brainstorm` / `design` modes, frame prompts to produce proposals; for `review` / `audit`, frame for findings.

If no domain in the registry substantially covers a concern, synthesize a session-based virtual expert role rather than forcing a mismatched registry entry.

Select the prompt template and conditional inputs to pass:

| `mode` | Prompt template source | Inputs to inject |
|--------|------------------------|------------------|
| Any open-ended mode (`review`/`audit`/`brainstorm`/`design`/`research`/`synthesis`) | `bridge-commons` Agent Prompt Template | `scope`, `task_description`, `task_type`, `mode`, `domains`, `context_summary`, `intensity` |
| `finding-driven` | Finding-Driven Mode reference (domain-expert prompt + IC prompt) | All of the above, PLUS `findings`, `fixes_applied`, `original_proposal`, `prior_session_id` (the last three may be empty strings — the prompt templates self-disable corresponding checks when inputs are absent) |

**Tier 0 in finding-driven mode is forbidden.** Tier 0 has no IC role, so Check #4 (fix-interaction) cannot run, and finding-driven without all four checks is misleading. If the user explicitly requests Tier 0 + finding-driven → halt with: `"Tier 0 + finding-driven is contradictory. Use Tier 1 for in-runtime four-check, or Tier 0 + review mode for trivial single-agent review."`

**Tier 2+ in finding-driven mode:** the runtime adapters' `runtime_input` payload MUST include the four finding-driven fields. See Phase 4 Dispatch (`[skills-root]/uacp-council/references/phase-4-dispatch.md`) for the extended schema.