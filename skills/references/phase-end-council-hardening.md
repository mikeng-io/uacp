# Phase-End Council Hardening Pattern

Use this reference after a phase-end Agent Council returns `CONCERNS` for UACP runtime/governance work.

## Pattern from governed canonical writer hardening

1. **Treat CONCERNS as actionable before RESOLVE.** Do not move into the next phase just because deterministic probes passed. Synthesize council findings into:
   - `resolved` now
   - `accepted_risk` for the current phase
   - `deferred` with owner/phase/acceptance criteria
   - `open` blockers

2. **Fix small boundary concerns immediately when they sit under the next phase's foundation.** For writer/tool boundaries, this includes:
   - hardening path resolution against absolute paths, `.`/`..`, root targets, directory targets, and symlink escapes
   - adding distinct policy categories when a canonical boundary is more specific than generic `file.write`
   - extending live probes with positive and negative cases, not only happy-path proof

3. **Verification artifact shape.** Record a bounded verification artifact that states:
   - authority artifacts that justified the hardening
   - exact concerns resolved by ID
   - checks run and result counts
   - any manual fallback used and why it is not normal enforcement
   - remaining deferred items with phase placement

4. **If the live tool schema is stale, use a narrow manual-drill fallback only for evidence artifacts.** Directly invoking the UACP-owned guarded handler with full UACP context is acceptable for a bounded verification artifact when the current long-running session misclassifies the exposed tool surface. Record this as a manual fallback and re-check from a fresh runtime/session later. Do not describe it as normal enforcement.

5. **Commit only after verification.** Run syntax/YAML checks and the relevant live proof harness before committing/pushing the UACP private repo. Do not touch or push Hermes Agent unless explicitly requested.

## Example concern-to-fix mapping

- `C001 path hardening` -> reject absolute/root/current/parent/directory/symlink escape paths; add negative tests.
- `C002 canonical writer classified as generic file.write` -> introduce `docs.uacp` / `config.uacp` categories or document an explicit accepted risk.
- `tool reload deferred` -> leave deferred until fresh-session verification, not a blocker for implementation correctness.
