# 02 — Naming and Nortrix Correction

## Naming candidates discussed

- `EVIDENCE`
- `MEMEX`
- `Recall`
- `Atlas`
- `Index`

## Early answer

At first, `UACP Recall` was suggested as a short practical name, with “Evidence Memory” as the formal description.

Later, after checking Trustless naming, the recommendation shifted to `UACP MEMEX`.

## Why not EVIDENCE

Mike liked `EVIDENCE`, but suspected the name was already used elsewhere.

Inspection confirmed that **evidence is already heavily occupied** in Trustless/UACP-adjacent language:

- proposal evidence
- verification evidence
- evidence packs
- evidence artifacts
- evidence records
- evidence validators
- `G3 Evidence`
- `evidence_service`
- OpenSpec historical evidence

Therefore, naming the module `EVIDENCE` risks confusion:

```text
Is EVIDENCE the folder?
Is it proof material?
Is it verification output?
Is it the retrieval module?
Is it the evidence service/runtime surface?
```

## Why not Recall

Trustless already has first-class recall concepts:

- `.agents/skills/recall`
- `.trustless/foresight/recall_bridge.py`
- daily/weekly/monthly evolution recall jobs

So `Recall` is better used as an operation/output, not the module name.

## Why not Foresight

Trustless already uses Foresight as an effectiveness/predictive layer. It should remain a layer/function, not the UACP module name.

## Why MEMEX

`MEMEX` had clean namespace properties:

- no major collision found in the inspected ecosystem,
- implies associative memory rather than raw evidence storage,
- can hold evidence, patterns, scores, and recall packets,
- does not sound like legal/crime-scene evidence,
- fits the “memory organ” role.

Recommended terminology:

```text
Module: MEMEX
Data: Evidence
Action/output: Recall Packet
Prediction/effectiveness layer: Foresight
Score: BES
```

## Formal description

```text
UACP MEMEX is the governed associative memory and retrieval layer for UACP.
It indexes evidence, lessons, council findings, warnings, transitions, and verification outcomes, then produces phase-aware recall packets ranked by authority, relevance, recency, and BES-style effectiveness.
```

## Nortrix correction

Mike corrected that Nortrix should not be used as the name for this module/bank.

Ground-truthed definition:

```text
Nortrix                 ← philosophical container / legal entity
  ├── public surfaces   ← nortrix.io, mikeng.io
  ├── substrate         ← nortrix-infrastructure, nortrix-services
  ├── projects          ← Trustless, Cortex, personax
  └── query channels    ← Norty
```

Important distinctions:

```text
Nortrix ≠ Norty
Nortrix ≠ UACP
Nortrix ≠ MEMEX
Nortrix ≠ the UACP evidence/retrieval bank
```

Corrected line:

```text
Nortrix remains the umbrella/container.
MEMEX is UACP’s internal memory/retrieval organ.
```
