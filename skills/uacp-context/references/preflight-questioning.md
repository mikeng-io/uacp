# Phase 8: Preflight Questioning (Inline, Conditional)

If `preflight_needed: true`, ask up to 3 targeted questions **one at a time** to resolve missing signals. Do NOT spawn a separate skill — handle inline.

**Rules (from superpowers brainstorming):**
- **One question at a time** — never bundle
- **Multiple choice preferred** — easier than open-ended
- **Maximum 3 questions** — if still unclear after 3, make reasonable assumptions and proceed
- **Stop when scope is clear** — don't ask what you can infer

**Question priority:**

**Q1 — What to analyze** (if `artifact_identified: false`):
> "What should I analyze? For example: specific files or directories, a UACP artifact, a topic you've been working on, or something else?"

**Q2 — Intent** (if `intent_clear: false`):
> "What kind of work are you looking for?"
> Options: Review / Audit / Verify / Research / Explore / Plan / Implement / Brainstorm

**Q3 — Domain focus** (if `domains_detectable: false` and artifact is ambiguous):
> "Any particular areas to focus on?"
> Options: (generate from domain-registry signals based on what's known so far)

After questions are answered, re-run signal resolution and update confidence.
