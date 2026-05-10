# UACP First Principles

## Triage First, Then Stable Phases

Every request starts with triage: scope calibration, granularity scoring, and governance routing. Work that deserves UACP then enters the stable phase envelope. The gates inside a phase are selected by context so UACP can govern many domains without forcing software-only assumptions onto every task.

## Evidence Over Assertion

Phase decisions should be based on artifacts, cluster outcomes, and explicit reasoning. When evidence is missing and the risk matters, UACP blocks or asks for authority instead of inventing certainty.

## Context Before Checklist

Every decision point starts with classification: domain, artifact type, side effects, risk, reversibility, trust boundary, ambiguity, and need for current facts. The result determines which clusters are required, optional, not applicable, or generated.

## Invariants Are Not Optional

Authority, declared side effects, write containment, privacy and safety constraints, traceable state, and conservative failure apply across all domains.

## Bounded Execution

EXECUTE work should be decomposed into bounded units through Hermes Kanban. The main Hermes/Norty orchestrator synthesizes and routes; heavy implementation belongs to delegated workers or external coding agents when selected.

## Retrieval-Led Learning

Gate selection should improve by retrieving similar prior scenarios and ranking candidate clusters by historical usefulness, risk similarity, and observed outcomes. Stage 1 and Stage 2 only create local storage and schemas for this future loop.

## Separation of Concerns

- UACP owns governance, artifacts, phase transitions, and learning records.
- Hermes Kanban owns durable task graph and progress visibility.
- Delegated workers own bounded execution units.
- Honcho owns personal and peer memory.
- Future Knowledge Bank owns shared retrieval and ranking.
- Cortex may consume and produce knowledge, but should not be the only owner.
