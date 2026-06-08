# Phase 4: Synthesis (standard + thorough only)

**Rationale:** Multiple domain experts often find the same root issue from different angles (a missing input validation shows up in security, API, and testing domains independently). Without synthesis, the final report over-counts the same problem. Merging also reveals when "two issues" are actually one issue that's been inflated by being described separately — or genuinely different issues that need separate remediation.

Identify merge opportunities:
- Findings with >70% description overlap → propose merge
- Merged findings inherit highest severity
- Both origin reviewers must agree to merge

Update finding states:
- `confirmed` — defended and/or corroborated by ≥ consensus_threshold of reviewers
- `withdrawn` — reviewer withdrew after challenge
- `disputed` — challenged but not resolved
- `merged` — two findings consolidated
- `discovered` — emerged during challenge rounds
