# Operator phase-return presentation

Session learning: Mike corrected UACP reporting style. Phase returns to Telegram/Discord must provide information, not raw audit data.

## Rule

Separate two surfaces:

- Evidence layer: full raw artifacts, paths, diffs, validation logs, council findings, gate-ledger records, rollback evidence.
- Operator summary layer: concise conclusion and decision-grade context for the human control channel.

Default phase returns must use the operator summary layer. Raw evidence stays in artifacts and should be referenced by pointer, not pasted into chat.

## Required summary shape

1. Conclusion: phase + status + one-sentence result.
2. What changed: one to three meaning-level bullets; do not list every file.
3. Why it matters: rational intent / consequence.
4. Decision: pass, warn, block, or in-progress with rationale.
5. Invariants: preserved constraints that matter.
6. Risks: only material residual risks and handling.
7. Next: recommended next action and whether operator input is required.
8. Evidence pointer: commit, artifact index, verification summary; say raw details are available on request.

## Suppress by default

- full edited-file lists
- newly-created-file lists
- raw `git diff --stat`
- raw validator logs
- raw council transcripts
- complete artifact inventories

Include specific paths only when the path is itself the decision subject, a blocker/error depends on it, rollback requires it, or Mike explicitly asks for audit details.

## Invariant

This is a presentation rule only. Do not weaken evidence capture, Heartgate, Guardian, validator, council, or gate-ledger requirements.