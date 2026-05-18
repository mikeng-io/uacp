# Open Questions

## Scope

1. Is SEF a Nortrix-level substrate, a standalone service, or a library first?
2. Should SEF have its own repo immediately, e.g. `nortrix-labs/semantic-event-fabric`, or start as design artifacts only?
3. Should QMD be created before SEF implementation because retrieval duplication already exists in four+ places?

## Database

1. Is Neo4j acceptable as the default dedicated-service graph DB?
2. Should FalkorDB, PostgreSQL+AGE, ArangoDB, SurrealDB, or another graph/multimodel store be evaluated first?
3. What operational constraints matter most: local-first, backup simplicity, visualization, query power, or service maturity?

## QMD

1. Is QMD the right name: Query Mediation Daemon/Service?
2. Should QMD expose a source-scoped recall packet API used by SEF, UACP MEMEX, Cortex, Trustless, and Hermes memory?
3. Should QMD own reranking, or should each source return its own ranking plus evidence?

## UACP relationship

1. Should SEF be UACP-aware only, or eventually a UACP-integrated infrastructure module?
2. What SEF events should UACP MEMEX index as evidence?
3. Should BES score alias resolution, route reliability, dispatch outcomes, or only governed patterns inside UACP MEMEX?

## Public/private boundaries

1. What graph view may Nora see?
2. Should Nora consume SEF events directly or only resolved dispatch commands?
3. How should private-to-public minimization be represented in the event/proof schema?

## Models

1. Which multilingual embedding/reranker stack should be evaluated first?
2. Should resolver/high-judgment roles use Hermes configured provider routing rather than SEF-local model config?
3. What confidence thresholds should trigger auto-resolve vs clarification?

## MVP

1. First adapter: WhatsApp, Discord, or a fake/local adapter?
2. First target: Mike-only test, one dinner group, or a synthetic fixture group?
3. Should implementation wait until QMD design is captured, or can SEF MVP proceed with stub retrieval?

## Non-actions captured

- No implementation started.
- No DB installed.
- No service created.
- No UACP protected state changed.
- No Nora/WhatsApp dispatch attempted.
