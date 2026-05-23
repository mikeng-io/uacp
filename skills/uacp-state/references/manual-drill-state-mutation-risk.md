# Manual-drill state mutation risk

Use this reference when a UACP run needs state/artifact writes but the current runtime does not expose a complete guarded `uacp_state_write` surface.

## Principle

A manual-drill bypass may be acceptable only for local, reversible UACP artifact work with explicit operator authority. It is never proof of production enforcement and must not be normalized as the runtime path.

## Required artifact wording

Record a finding similar to:

```yaml
findings:
  - id: EXEC-F1
    severity: high
    state: accepted_risk
    summary: "Manual-drill state/artifact writes used a local execution path because guarded runtime state mutation was unavailable or blocked in this tool surface."
    evidence: "Ordinary file/shell mutation was blocked for missing UACP context fields; local write path was used to complete reversible artifacts."
    recommendation: "Accept only for this local drill; block production-runtime claims until uacp_state_write/Heartgate lifecycle wiring is active and proved."
    owner: "future runtime hardening run"
```

## Verification expectations

- Validator/YAML checks may prove artifact parseability, not runtime enforcement.
- Final verification should close as `concerns` or `warn` if bypass risk remains accepted/deferred.
- A resolution artifact should explicitly state: closed for design/manual-drill scope only, not production runtime activation.

## Do not do

- Do not claim Guardian/Heartgate production enforcement from a bypassed manual drill.
- Do not silently update `state/current.yaml` without a run manifest and provenance.
- Do not convert this reference into a blanket instruction to use a specific bypass tool; tool behavior may change as Guardian hardening improves.
