# 05 — Extraction, Retrieval, Creation

Mike asked to examine:

```text
1. Extraction way
2. Retrieval way
3. Creation way
```

And asked whether MEMEX should live in Heartgate.

Answer:

```text
No. MEMEX should not live in Heartgate.
MEMEX should live beside the lifecycle.
Heartgate should consume and validate MEMEX output, not own MEMEX.
```

## Placement

```text
MEMEX lives beside the lifecycle.
Heartgate checks MEMEX integrity at phase boundaries.
Guardian protects MEMEX mutation/runtime boundaries.
RESOLVE is the main creation/update point.
```

Architecture sketch:

```text
UACP
├── Lifecycle phases
│   ├── TRIAGE
│   ├── PROPOSE
│   ├── PLAN
│   ├── EXECUTE
│   ├── VERIFY
│   └── RESOLVE
│
├── MEMEX
│   ├── Extractor
│   ├── Index
│   ├── Retriever
│   ├── BES Scorer
│   └── Recall Packet Builder
│
├── Heartgate
│   └── validates phase transition coherence + MEMEX packet integrity
│
└── Guardian
    └── enforces allowed MEMEX reads/writes/tools
```

Rule:

```text
MEMEX informs Heartgate.
Heartgate does not become MEMEX.
```

## 1. Extraction flow

Extraction means:

```text
What can become a MEMEX item?
```

Sources:

- `state/runs/*`
- `verification/*`
- `plans/*`
- `outputs/uacp-current-status.yaml`
- council synthesis artifacts
- Heartgate transition artifacts
- warnings
- deferred items
- resolved lessons
- skill references
- runtime enforcement findings

Extraction must be typed. No random chunks.

Extraction modes:

### Passive extraction

```text
artifact → candidate items → validation → index
```

### Resolve extraction

At `RESOLVE`, UACP deliberately asks:

```text
What did we learn?
What pattern should be preserved?
What warning should recur in future packets?
What was noise?
What should be retired?
```

RESOLVE is the cleanest place for durable lessons.

## 2. Retrieval flow

Retrieval means:

```text
Given this UACP phase/task, what prior memory should be injected?
```

Retrieval should happen at:

- phase entry,
- before Council dispatch,
- before Heartgate transition when material risk exists.

Example query:

```yaml
query:
  phase: PLAN
  domain: runtime-enforcement
  surface: guardian-plugin
  risk_tags:
    - authority-boundary
    - state-mutation
    - prompt-injection
```

Example Recall Packet:

```yaml
recall_packet:
  packet_id: memex.packet.20260515.abc123
  query_context:
    phase: PLAN
    domain: runtime-enforcement
  selected_items:
    - id: memex.uacp.phase4.containment.fail_closed
      reason: same runtime boundary + prior blocker
      score_breakdown:
        lexical: 0.72
        domain: 0.95
        authority: 1.00
        bes: 0.81
        recency: 0.90
  known_failure_modes:
    - Do not treat evidence checker as actual containment.
    - Do not mutate UACP state outside governed writer.
  required_reads:
    - references/contained-shell-execution-seam-20260514.md
  council_seed_questions:
    - Does this plan preserve Guardian kernel/adapter separation?
  exclusions:
    - id: memex.old.agent_skills_guardian
      reason: superseded by UACP canonical docs
```

Initial retrieval should be structured + lexical, not vector-first.

MVP ranking:

```text
phase match
+ domain match
+ surface match
+ authority level
+ recency
+ BES
+ keyword/semantic match
```

Later:

```text
BM25 + embeddings + reranker + BES/authority post-rank
```

## 3. Creation flow

Creation is more dangerous than extraction.

Creation means:

```text
When does UACP create or update a MEMEX item or BES score?
```

Creation must be governed.

Allowed creation paths:

- RESOLVE,
- explicit MEMEX proposal/update task,
- verification/council accepted finding promoted by governed writer,
- Heartgate warning/deferred item promotion,
- operator-approved bootstrap/update artifact.

Important rule:

```text
Retriever is read-only.
Scorer proposal is advisory.
Governed writer applies updates.
```

Flow:

```text
MEMEX retrieve → no mutation
MEMEX suggest BES delta → no mutation
RESOLVE / governed writer → mutation
```

## Heartgate responsibilities

Heartgate gets three MEMEX-related responsibilities only:

1. Require MEMEX packet where appropriate.
2. Validate MEMEX packet integrity.
3. Record MEMEX adequacy as transition evidence.

Heartgate should not:

- run the indexer,
- own the pattern registry,
- mutate BES,
- decide what lessons exist,
- become the retrieval engine.
