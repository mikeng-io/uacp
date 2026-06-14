<!-- Golden fixture: uacp.intent (TRIAGE->PROPOSE charter) -->
<!-- Minimal VALID instance: per config/artifact-schemas.yaml `intent.required_sections`
     this artifact is a Markdown doc (path_template proposals/{run_id}-intent.md),
     NOT a YAML mapping. It must contain the four required section headings below. -->

# Run Intent — uacp-fixture-001

## Success Definition
The minimal lifecycle run reaches RESOLVE with all gates passing.

## Explicit Out-of-Scope
Anything not required to exercise the lifecycle harness.

## Termination Condition
Run finalizes at RESOLVE, or a Heartgate blocker halts it.

## Authority Source
operator-request (fixture).
