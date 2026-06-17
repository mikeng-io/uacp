# Codebase Verification Review Pattern

Use this reference when acting as a **verification reviewer** at a UACP phase gate (typically PROPOSE → PLAN, or before EXECUTE enable) for a codebase change. The goal is to inspect the existing code, tests, and design docs; identify gaps between declared intent and actual coverage; and produce a structured review artifact that blocks or permits the next phase.

## Trigger

Use this pattern when:
- A UACP PROPOSE asks to implement or enable a live pipeline change (e.g. x-draft revamp, new gates, language modes).
- The operator asks you to "review what tests/dry-run fixtures and acceptance evidence are required before implementing or enabling live changes."
- You need to verify that existing tests, gates, and dry-run behavior actually cover the proposed changes before PLAN is approved.

## Sequence

1. **Discover the codebase structure**
   - `find <repo> -maxdepth 3 -type d -name "<component>*"`
   - `ls -la <repo>/src/<component>/`, `<repo>/tests/`, `<repo>/config/`
   - Identify the main activities, workflows, config files, and test directories.

2. **Map existing test coverage**
   - List all test files (`ls tests/test_activities/ tests/test_workflows/`).
   - Read each test file to understand what it covers.
   - Build a coverage matrix: test file → lines → what gates/behaviors it exercises.
   - Run targeted tests to confirm they pass: `uv run pytest <paths> -q`.

3. **Read the implementation under review**
   - Read the main activity/workflow files that will change.
   - Read the config files (`config/*.yaml`) that govern behavior.
   - Read design docs (`docs/design/`) that declare intent.
   - Cross-reference design intent with implementation reality.

4. **Identify gaps**
   - For each proposed new capability (content diversity, language modes, stance ledger, etc.), ask:
     - Is there a gate/activity for this? If not, it needs implementation.
     - Is there a test for this? If not, it needs tests.
     - Is there a dry-run fixture that exercises this? If not, it needs fixtures.
   - For each existing gate, ask:
     - Does the test prove the gate actually blocks what it claims to block?
     - Does the dry-run path prove no side effects leak through?

5. **Define required tests and fixtures**
   - For each gap, specify:
     - Test name and location (`tests/test_activities/test_<gate>.py`).
     - Fixture shape (mock bundle, mock DB state, mock ledger).
     - Expected pass/fail behavior.
   - Specify dry-run fixtures that prove side-effect isolation.

6. **Compile blockers, concerns, and suggestions**
   - **Blockers**: items that must resolve before PLAN. Number them (B1, B2, …).
   - **Concerns**: items that should be tracked. Number them (C1, C2, …).
   - **Suggestions**: improvements that improve robustness without blocking. Number them (S1, S2, …).

7. **Write the acceptance evidence checklist**
   - A checklist of verifiable items that must be true before live enable.
   - Include: test pass evidence, dry-run smoke evidence, manual review evidence, live smoke evidence.

8. **Produce the review artifact**
   - Write a markdown file under `docs/design/` or `verification/`.
   - Structure: Current State → Test Coverage Matrix → Gaps → Required Tests/Fixtures → Blockers/Concerns/Suggestions → Acceptance Checklist.
   - Reference the artifact from the PROPOSE → PLAN transition.

## Typical outputs

- `docs/design/<topic>-verification-review.md` or `verification/<run_id>-review.md`
- Updated test coverage matrix
- List of new test files to create
- List of fixture files to create
- Acceptance evidence checklist

## Common pitfalls

- **Reading design docs but not the code.** The design may claim a gate exists, but the code may not wire it. Always ground-truth the implementation.
- **Assuming dry_run safety from a flag check.** A single `test_dry_run_flag_defaults_false` does not prove side effects are skipped. Prove the actual sinks (DB write, Discord post, API call) are bypassed.
- **Listing gaps without specifying the test/fixture shape.** A gap without a concrete test definition is not actionable for PLAN.
- **Forgetting to cross-reference invariants.** If the codebase has documented invariants (e.g. the `AGENTS.md` evidence-must-be-produced invariant), verify they are actually enforced in the code under review.
- **Not running existing tests.** Always run the existing test suite before claiming coverage is understood. A failing test may indicate the codebase is in a dirty state that invalidates the review.

## Example: Cortex x-casual verification review

See `cortex/docs/design/editorial-mass-restructure/x-draft-verification-review.md` for a concrete example produced by this pattern. It covers:
- Single-shot composer pipeline inspection
- 11 test files analyzed (~2,300 lines)
- Gap analysis for content diversity, language modes, stance ledger
- 15 required tests/fixtures defined
- 5 blockers, 5 concerns, 6 suggestions
- 8-item acceptance checklist
