---
type: policy
title: UACP First Principles
description: Foundational reasoning axioms that all UACP governance, orchestration, and execution decisions derive from.
tags: [first-principles, governance, cognitive-separation, evidence]
timestamp: 2026-06-18
---

# UACP First Principles

## The Conformance Loop for Semantic Work

UACP exists to **reduce the long-run friction of cooperation** on work done by *semantic* (non-deterministic) actors — agents and the humans who direct them. Governance is a **time-asymmetric** trade: it adds friction at the point of interaction (declaring intent, passing gates, producing evidence) and repays it over the pipeline's lifetime — later work runs on rails, is not re-derived, is not re-litigated, and does not silently drift.

The governed **atom** is **conformance**: *does the realized reality match the declared intent?* It takes the form of a running loop, not a static document, because of the **semantic differentia** — the executor is semantic, so it can neither be trusted to **infer the spec** (intent must be **externally declared**) nor to **certify its own pass** (verification must be **externally witnessed**). The loop's defining commitment is **refusal-to-drift**: the binding between the declared side and the witnessed side is a governed primitive, checked at every transition, never allowed to decay.

**Coherence** — a system consistent with itself, its claims bound to evidence — is the product this discipline manufactures; the purpose above is why the product is worth its price. The principles that follow (triage-first, evidence-over-assertion, cognitive separation, bounded execution) are the *means* to this end. Full rationale: `design/telos/` (the purpose) and `design/comprehend-measure-serialize/` (the comprehend → measure → serialize discipline that instantiates the loop at a single grain).

## Triage First, Then Stable Phases

Every request starts with triage: scope calibration, granularity scoring, and governance routing. Work that deserves UACP then enters the stable phase envelope. The gates inside a phase are selected by context so UACP can govern many domains without forcing software-only assumptions onto every task.

## Evidence Over Assertion

Phase decisions should be based on artifacts, cluster outcomes, and explicit reasoning. When evidence is missing and the risk matters, UACP blocks or asks for authority instead of inventing certainty.

## Context Before Checklist

Every decision point starts with classification: domain, artifact type, side effects, risk, reversibility, trust boundary, ambiguity, and need for current facts. The result determines which clusters are required, optional, not applicable, or generated.

## Invariants Are Not Optional

Authority, declared side effects, write containment, privacy and safety constraints, traceable state, and conservative failure apply across all domains.


## Cognitive Separation

UACP separates governance cognition, deliberative cognition, coordination memory, execution loops, and actuation/evidence surfaces.

- UACP governs authority, phases, risk, human involvement, and evidence obligations.
- Agent Council supplies deliberative multi-perspective cognition when single-agent reasoning is insufficient.
- The coordination adapter records durable coordination state; it is not the governance brain and not the deliberation engine.
- Agent runtimes and delegated workers execute bounded work under propagated UACP/council context.
- Tool adapters and evidence services observe or act; they do not own policy.

This separation is a reasoning invariant, not only a runtime wiring choice.

## Bounded Execution

EXECUTE work should be decomposed into bounded units with the coordination adapter as the durable task substrate. For non-trivial implementation, Agent Council provides the role-aware orchestration topology over those bounded units: decomposition, worker assignment, adversarial checking, integration critique, and synthesis. Heavy implementation belongs to delegated workers, external coding agents, browser/computer-use automation, web extraction/search services, or other approved execution/evidence adapters when selected by PLAN and guarded by UACP authority, side-effect, and containment rules.

## Retrieval-Led Learning

Gate selection should improve by retrieving similar prior scenarios and ranking candidate clusters by historical usefulness, risk similarity, and observed outcomes. Stage 1 and Stage 2 only create local storage and schemas for this future loop.

## Separation of Concerns

- UACP owns governance, artifacts, phase transitions, and learning records.
- The coordination adapter owns durable task graph and progress visibility.
- Delegated workers own bounded execution units.
- A personal/peer memory store owns personal and peer memory.
- The Knowledge Bank owns shared retrieval and ranking.
- An external knowledge service may consume and produce knowledge, but should not be the only owner.
