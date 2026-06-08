## Step 7: Synthesis & Verdict

Combine outputs into the unified council report. **Verdict routes by `mode` first, then `task_type`** — see `bridge-commons/SKILL.md` "Verdict Logic" for the canonical tables.

Routing summary:

- `mode == "finding-driven"` → use the finding-driven verdict table (canonical in `bridge-commons`). The presence of design-drift / regression / fix-interaction findings can flip a "all addressed" verdict to `CONCERNS`. **Takes precedence over `task_type` routing.**
- `mode` in {`brainstorm`, `design`, `research`, `synthesis`} → no verdict (`verdict: null`). Output proposals / observations / synthesis records instead.
- Otherwise route by `task_type`: `review`/`analysis` use the standard severity table; `audit` uses the compliance-calibrated table.

Refer to `bridge-commons` for the exact verdict conditions. Do not duplicate them here.