<!-- The PR title, type: label, assignee, and branch name are enforced by the PR Policy
     workflow — no need to repeat them here. Fill what is relevant; delete the rest,
     including these comments. Trivial PRs may be just What + Verified. -->

<!-- One sentence on why this matters, if the title alone doesn't say it. -->

## What

<!-- What changed. Bullets for a focused change; a table for multi-phase work (cf. #47). -->

## Verified

<!-- How we know it's correct — be specific, numbers/commands matter (Invariant #5).
       - Suite: `pytest` — N passed, M skipped. Ruff + pyright clean.
       - Kernel / Guardian: `scripts/live_guardian_probe.py` — no NEW failures.
       - Plugin / install surface: real `claude plugin install` + `claude mcp list`.
       - Lifecycle / verify: relevant `scripts/phaseN_verify.py` run.
     "Tests green" with no count or command is not evidence. -->

## Review

<!-- Required when this PR touches kernel code, policy YAML, or canonical docs under docs/
     (Invariant #4) — note that a docs: change to canonical docs/ DOES require this:
     state who reviewed, material findings, and remediation. Council must include at least one
     cross-provider reviewer (kimi / codex / gemini) — same-provider-only is self-attestation by
     proxy. Zero unresolved material findings to merge. Delete ONLY if the PR touches none of those
     (e.g. a chore/ci/test-only change, or a non-canonical README outside docs/). -->

## Links

<!-- ADR, decision-log entry, or UACP run_id this PR implements/closes. Delete if none. -->

## Deferred

<!-- Explicit scope boundary: what is intentionally NOT in this PR, and why. Delete if none. -->
