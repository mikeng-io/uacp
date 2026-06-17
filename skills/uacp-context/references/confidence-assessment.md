# Phase 7: Determine Confidence and Surface Missing Signals

Check each signal explicitly:

```yaml
signal_resolution:
  artifact_identified: true | false    # specific files/paths/topics clearly present?
  intent_clear: true | false          # review? audit? verify? research? implement? plan?
  domains_detectable: true | false    # can domains be matched from the domain registry?
  scope_bounded: true | false         # is scope narrow enough to proceed without clarification?
  uacp_state_clear: true | false      # does active UACP state constrain or inform this work?
```

Build `missing_signals` list from any `false` signal:

```yaml
missing_signal_map:
  artifact_identified: false  →  "artifact"
  intent_clear: false         →  "intent"
  domains_detectable: false   →  "domains"
  scope_bounded: false        →  "scope"
  uacp_state_clear: false     →  "uacp_state"
```

Derive overall confidence:

```yaml
confidence_levels:
  high:    all signals true  →  preflight_needed: false
  medium:  1 signal false    →  preflight_needed: true  (scope or domains)
  low:     2+ signals false  →  preflight_needed: true  (artifact or intent unresolved)
```
