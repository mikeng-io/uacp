# Rationale

## Why this capture exists

Mike has repeatedly corrected the direction of the UACP skill work: the problem is not merely missing prose; the problem is structural. The current UACP artifacts do not reflect the real design discussion because they centralize too much into shared documents and thin phase wrappers.

## Why one document is insufficient

A single roadmap/document loses operational detail because UACP has multiple distinct concerns:

- rationale and history of failure
- current-state audit
- phase-local skill ownership
- detailed per-skill Explore/Determine/Decision/Review/Audit/Implement loops
- measurement and validation
- memory/recall rules
- risk handling
- implementation sequencing

Putting these in one file recreates the anti-pattern being fixed: a mega-SOP that claims coverage while hiding missing details.

## Correct preservation approach

Use a split artifact package. Each file owns one concern. This mirrors the target skill architecture: concise entrypoints plus detailed local supporting files.

## Core rationale

Current UACP should be treated as broken for this refactor. It must not self-certify or govern the refactor. Use normal repo/file workflow, deterministic checks, and independent review.
