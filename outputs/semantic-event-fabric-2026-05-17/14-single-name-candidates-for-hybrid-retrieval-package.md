# Addendum: Single-Name Candidates for Hybrid Retrieval Package

Date: 2026-05-17
Status: naming refinement

## Correction

Mike wants a single proper name similar to `MEMEX`, not a descriptive phrase such as `Recall Fabric`.

The name should represent a hybrid retrieval package/library/protocol that includes:

- semantic/vector retrieval;
- keyword/full-text retrieval;
- query expansion;
- reranking;
- optional BES weighting;
- recall packet assembly;
- source-owned state invariant.

## Naming direction

Avoid names that sound like generic product categories:

- Semantic Search Kit
- Hybrid Retrieval Kit
- Recall Fabric
- Query Mediation Service

Prefer short coined names that can become module names.

## Strong candidates

### 1. LEXA

Rationale: lexical + semantic retrieval; short, pronounceable, neutral.

Meaning:

```text
LEXA = lexical/semantic access layer
```

Pros:
- captures keyword + semantic blend;
- short like MEMEX;
- good package name (`lexa` or `nortrix-lexa`);
- not UACP-specific.

Cons:
- may sound more keyword/search-oriented than recall/evidence-oriented.

### 2. NEXUS

Rationale: connecting multiple retrieval sources and ranking signals.

Pros:
- strong substrate feel;
- source federation implied.

Cons:
- common/overused name; package/repo conflicts likely.

### 3. VECTRA

Rationale: vector + retrieval/access.

Pros:
- memorable;
- search/retrieval connotation.

Cons:
- too vector-biased; does not express keyword/BES hybrid nature.

### 4. RECALLA

Rationale: recall-oriented equivalent of MEMEX.

Pros:
- clear relationship to recall packets;
- single name.

Cons:
- less elegant; may sound product-y.

### 5. ORBIS

Rationale: circle/world of sources; brings multiple retrieval signals into one orbit.

Pros:
- neutral, single name;
- good for multi-source query fabric.

Cons:
- meaning less obvious.

### 6. LUMEN

Rationale: surfaces relevant evidence/knowledge by illumination.

Pros:
- clean and memorable;
- broad enough for recall/retrieval.

Cons:
- common name; not specifically hybrid search.

### 7. ALETIA / ALETHEIA-derived

Rationale: truth/unconcealment; surfaces evidence.

Pros:
- philosophically aligned.

Cons:
- spelling/pronunciation complexity; risk of sounding too grand.

## Current recommendation

Use **LEXA** as the working name.

Definition:

```text
LEXA is a source-owned hybrid retrieval package for lexical, semantic, reranked, and optionally BES-weighted recall across Nortrix systems.
```

Expanded invariant:

```text
LEXA retrieves and ranks.
MEMEX recalls governed UACP evidence.
SEF resolves events/entities and proves authority.
BES weights where source-owned.
```

## Package naming

Possible package/repo names:

```text
lexa
nortrix-lexa
lexa-core
lexa-adapters
```

If `LEXA` is unavailable or too search-sounding, second choice is **ORBIS** for a broader multi-source retrieval substrate.
