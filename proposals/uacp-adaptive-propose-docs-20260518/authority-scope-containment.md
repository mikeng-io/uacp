# Authority, Scope, and Containment

## Authority

Authority source: Mike's explicit current-session instruction to proceed.

This is a UACP self-improvement patch lane. Because it affects UACP semantics, use lifecycle rhythm and governed artifacts, but avoid recursive protected-state mutation beyond bounded docs/config/validator patching.

## In scope

- `uacp-propose` skill behavior
- adaptive proposal documentation reference
- proposal package selection artifact shape
- phase-transition package readiness rule
- validator package-selection checks
- Heartgate transition expectation
- Guardian policy clarification for proposal package artifacts
- LEXA as regression/proving case only

## Out of scope

- LEXA implementation
- LEXA PLAN progression
- runtime LEXA daemon or wiring
- broad UACP redesign beyond PROPOSE package selection
- importing OpenSpec/Trustless ACP fixed gates/domains/classifications

## Containment

Allowed write surfaces, when executed later:

- UACP proposal artifacts for this run
- `uacp-propose` skill and local reference files
- UACP config/validator/Guardian policy if PLAN approves
- fixtures under a controlled verification path

Forbidden without later explicit phase approval:

- production/runtime state mutation
- private memory indexing
- external posts/messages
- live service wiring
- destructive file deletion
