# Runtime Adapter Construction Guidelines

Use when moving UACP Guardian/Heartgate work from planning into runtime implementation in any host runtime.

## Key Guidelines

**Inventory first.** Start with a classification slice before writing code. Classify local changes into: unrelated local patches, generic runtime seams, UACP plugin/kernel work, accidental UACP leakage into core, governance-context propagation, and tests. This prevents mixing concerns and makes scope-risk visible early.

**Neutral kernel must not import host modules.** Keep the Guardian kernel inside the UACP plugin package or another neutral package, not the host runtime's core module tree. Runtime-specific provider inference (e.g., inferring tool provider from host session context) belongs in the adapter/plugin layer, not the kernel.

**Remove UACP-leakage anti-pattern.** Hardcoded UACP fallback logic inside generic core plugin plumbing is leakage. A function like `_uacp_builtin_guardian_block_message()` inside the host runtime's plugin manager is wrong; plugin-disabled behavior should not silently contain UACP doctrine.

**Governed writer scope.**
- `uacp_state_write` is the only state writer; restrict it to `state/`.
- `uacp_artifact_write` may write approved artifact roots: `plans/`, `proposals/`, `executions/`, `verification/`, `.outputs/`, `knowledge/`.
- `uacp_artifact_write` must reject `state/`, `docs/`, `config/`, absolute paths, and path traversal.

**DB migration sequencing.** Generalize the governance context API first; defer physical table renames until the migration is explicitly in scope. Wrappers can provide the generalized API without a schema change.

**Do not amend commits with mixed concerns.** If a local commit mixes unrelated working-tree changes with the UACP changes, separate or review the diff first. Amending that commit buries unrelated changes.
