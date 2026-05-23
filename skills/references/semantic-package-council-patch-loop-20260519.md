# Semantic package council patch loop — 2026-05-19

Use this reference when UACP work touches adaptive PROPOSE/PLAN packages, Markdown semantic substrate, validator gates, or council verification.

## Durable lesson

Do not treat semantic Markdown packages as optional presentation artifacts. YAML lifecycle files are the machine envelope; Markdown package directories are the recoverable semantic substrate for future agents and reviewers.

If a council or operator flags missing package semantics, fix the governing skills/validators/schema behavior first. Proposal-level backfills may repair an individual run, but they do not prevent recurrence.

## Council loop pattern

1. Dispatch a role-diverse council after the first implementation, not only after final polish:
   - governance reviewer;
   - validator/schema compatibility auditor;
   - devil's advocate/adversarial reviewer;
   - synthesis/debate lead.
2. Classify findings as BLOCK / CONCERNS / PASS with explicit severity.
3. Patch systemic HIGH/MEDIUM issues before reporting success.
4. Rerun a focused council over the patch delta until PASS or acceptable residual risk is explicit.
5. Record a compact synthesis artifact under `verification/` so future agents can recover the debate outcome without reading raw transcripts.

## Validator enforcement pattern

For adaptive package-selection artifacts, the validator should enforce recoverability, not merely check that referenced files exist:

- require canonical package directories:
  - `proposals/{run_id}/` for proposal packages;
  - `plans/{run_id}/` for plan packages;
- require `00-index.md` inside each package directory;
- require universal-core artifacts to point to readable Markdown inside that package directory;
- require selected-module artifacts to point to readable Markdown inside that package directory;
- treat empty `selected_modules` as BLOCK for package-selection artifacts, not WARN;
- block non-Markdown, unreadable, placeholder-thin, heading-less, or semantically deficient artifacts.

## Operator reporting pattern

Report the outcome as an information summary, not a raw inventory:

- conclusion first: initial result -> patch -> focused rerun result;
- meaning-level changes;
- why it matters;
- remaining residuals;
- compact evidence pointer: commit(s), validator command(s), synthesis artifact.

Avoid dumping full file lists, council transcripts, or validation logs unless Mike asks for audit detail.

## Acceptable residuals from this session

Shallow keyword/term matching and arbitrary minimum length thresholds are acceptable as minimum recoverability checks, but they are not semantic-quality proof. If future work depends on deeper assurance, add package-level coherence checks rather than pretending character counts prove understanding.
