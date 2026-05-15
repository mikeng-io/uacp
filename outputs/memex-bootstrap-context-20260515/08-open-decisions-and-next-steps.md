# 08 — Open Decisions and Next Steps

## Status

This capture preserves the MEMEX+BES design discussion as governed UACP output artifacts.

This is **not yet canonical doctrine** and does not mutate UACP docs/config/state.

## Settled points

### Name

```text
Module name: MEMEX
```

Avoid:

- `EVIDENCE` as module name — too overloaded.
- `Recall` as module name — already used in Trustless.
- `Foresight` as module name — already used as predictive/effectiveness layer.
- `Nortrix` as module/bank name — Nortrix is umbrella/legal/philosophical container.

### Role

```text
MEMEX = governed associative memory / retrieval layer.
BES = adaptive scoring / learning signal.
```

### Relationship to UACP

```text
MEMEX connects UACP memory.
BES teaches it what mattered.
```

But:

```text
MEMEX is memory, not authority.
BES is ranking, not approval.
```

### Relationship to Heartgate and Guardian

```text
MEMEX produces recall/extraction/score artifacts.
Guardian enforces presence/provenance/write boundaries.
Heartgate validates MEMEX adequacy at phase transitions.
RESOLVE/governed writers create or update durable MEMEX/BES state.
```

### Implementation classification

MEMEX implementation cannot initially be a normal UACP proposal.

It should be classified as:

```text
Control-Plane Bootstrap / Governance Substrate Patch
```

Reason:

```text
It modifies governance docs/config/runtime policy, so the normal Guardian-protected UACP path may block the work before the necessary enforcement surfaces exist.
```

## Open decisions

### 1. Bootstrap lane name and artifact location

Candidates:

- `Control-Plane Bootstrap Lane`
- `Governance Bootstrap Lane`
- `UACP Bootstrap Authority`

Need decide canonical location for bootstrap artifacts.

Possible location:

```text
UACP_ROOT/outputs/bootstrap/...
```

or eventually:

```text
UACP_ROOT/bootstrap/...
```

Only after canonical docs/config define it.

### 2. MEMEX artifact tree

Possible eventual topology:

```text
UACP_ROOT/memex/
  index/
    items.yaml
    patterns.yaml
    sources.yaml
  packets/
    *.yaml
  bes/
    scores.yaml

UACP_ROOT/config/memex.yaml
```

Need decide whether `memex/` is canonical data, generated output, or runtime state.

### 3. First enforcement stage

Recommended progression:

```text
Stage 0 — Advisory
Stage 1 — Required declaration
Stage 2 — Required packet for high-risk transitions
Stage 3 — Guardian enforcement for protected actions
Stage 4 — BES feedback enforcement
```

Need decide exact first patch scope.

### 4. BES authority factor

Need settle initial authority factor table.

Draft:

```yaml
council_reviewed_resolved_run: 1.00
heartgate_transition_warning: 0.95
verification_artifact: 0.90
accepted_deferred_item: 0.85
skill_reference: 0.75
draft_plan_note: 0.60
pre_tracking_legacy_note: 0.50
```

### 5. MEMEX writes

Need define whether MEMEX creation/update uses:

- existing `uacp_artifact_write`,
- new `uacp_memex_write`,
- or a later governed writer surface.

Strong recommendation:

```text
Retriever must remain read-only.
BES updates must be proposed first and applied only by governed writer.
```

## Immediate next actions

1. Review this capture package.
2. Decide whether `outputs/memex-bootstrap-context-20260515/` is the correct holding location.
3. If yes, remove or archive the temporary home-dir staging copy:

```text
/home/norty/memex-bes-context-20260515/
```

4. Create a small bootstrap authority artifact for MEMEX control-plane work.
5. Patch governance docs/config only after bootstrap scope is explicit.
6. Keep all first-stage MEMEX enforcement advisory/declaration-only until Guardian/Heartgate surfaces are ready.

## Temporary staging cleanup note

A temporary staging copy was initially created under:

```text
/home/norty/memex-bes-context-20260515/
```

This was corrected by writing the package to:

```text
UACP_ROOT/outputs/memex-bootstrap-context-20260515/
```

The temporary home-dir copy should be removed only with explicit cleanup authority, because deletion is irreversible.
