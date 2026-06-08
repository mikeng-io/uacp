## Tier Selection Quick Reference

| Situation | Tier |
|-----------|------|
| 1 trivial domain, no integration concerns | 0 |
| 2–5 domains, single-runtime review, fast turnaround | 1 |
| 5–10 domains, want toolchain/model-family diversity, independent verification | 2 |
| 9+ domains, irreversible/high-stakes decision, security/compliance, max confidence | 3 |
| Tier 1 returned 3+ disputed findings or `low` confidence | Escalate to 2 or 3 |
| Routine 2-domain code-style review | Tier 1 (not Tier 3) |

When in doubt, start at Tier 1 and let the tier-up rule escalate.

## Notes

- **Read GLOSSARY.md first.** Anti-patterns 1–7 in the glossary apply directly to this skill. Tier inflation/deflation and fabricated runtime outputs are the most common failure modes.
- **Mode is orthogonal to tier.** Any tier can run any mode (with the obvious exception: Tier 0 in brainstorm produces a single proposal, which usually isn't useful).
- **SKIPPED runtimes are non-blocking** at Tier 2/3. As long as one runtime returns COMPLETED, the council proceeds.
- **Tier escalation is a feature, not a fallback.** Use it deliberately when the lower tier reveals genuine uncertainty.
- **Capability profile flows through every dispatch.** `inspect` vs `modify` is set at the council level and translated to runtime-specific flags by each adapter.
- **Domain expansion via `cross_domain_signals` runs at every tier ≥ 1.** New domain experts can be added mid-debate when a finding has implications outside an expert's domain.
- **Diversity sources are recorded explicitly.** Never leave `diversity_sources` empty; if only role diversity is active, say so.
- **No fabrication.** If a runtime adapter is unavailable at Tier 2/3, mark it SKIPPED and proceed. Do not invent its output.