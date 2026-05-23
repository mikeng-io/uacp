# Heartgate Evidence Disposition and Reload Notes — 2026-05-18

Use this reference during VERIFY for governance/runtime changes that touch Guardian, Heartgate, validators, lifecycle gates, or plugin code.

## Evidence disposition files

Heartgate may require per-cluster evidence disposition files before VERIFY→RESOLVE.

For a cluster named `{cluster_id}` in run `{run_id}`, prepare:

```text
verification/{run_id}-{cluster_id}-verified-facts.md
verification/{run_id}-{cluster_id}-assumptions.md
```

The files are not arbitrary prose. They must include the expected headers/content markers:

- verified facts file: include lines beginning with `Fact:`
- assumptions file: include lines beginning with `Disposition:`

Example:

```markdown
# Verified facts — validator fixtures

Fact: Passing fixture validates with RESULT PASS.
Fact: Blocking fixture validates with RESULT BLOCK and names the expected blocker.
```

```markdown
# Assumptions — validator fixtures

Disposition: Fixture coverage is structural, not exhaustive semantic proof for every future proposal domain.
Disposition: Path existence checks assume UACP_ROOT-relative artifacts remain stable between validation and transition.
```

## Runtime/plugin reload pattern

If VERIFY patches plugin/kernel code, the live tool process may still be using a cached module. Do not claim full live enforcement only because file-level code changed.

Use a two-part proof:

1. Run the live tool path if available and record its result.
2. Directly import or invoke the edited module from disk to prove the new code path, especially for positive/negative fixtures.

If live reload is not proven, record an owned warning:

- owner
- residual risk
- reload/deployment next action
- whether local module proof is sufficient for this bounded run

## Negative fixtures matter

For enforcement gates, VERIFY should include a negative fixture that proves the gate blocks the missing or malformed case. A positive pass alone is not sufficient for governance/runtime enforcement claims.
