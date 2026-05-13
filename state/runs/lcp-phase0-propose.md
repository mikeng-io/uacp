---
kind: uacp.proposal
schema_version: "0.1"
run_id: lcp-phase0
phase: propose
created_at: "2026-05-11T12:51:00Z"
status: approved
---

# LCP Phase 0 — Proposal

## Objective
Create all foundation artifacts for LCP so Phase 1 (runtime implementation) has a canonical schema and config reference.

## Side Effects
- Creates directory tree under ~/.hermes/liaison/
- Creates directory under ~/.hermes/profiles/public/
- No Hermes config.yaml changes
- No gateway changes
- No runtime code

## Allowed Write Roots
- ~/.hermes/liaison/
- ~/.hermes/profiles/public/

## Forbidden
- ~/.hermes/config.yaml
- ~/.hermes/.env
- ~/.hermes/skills/
- ~/.hermes/uacp/docs/
- ~/.hermes/uacp/config/

## Verification Plan
1. All files exist at declared paths
2. YAML parses without errors
3. SQLite schema creates tables successfully
4. Guard policy doc covers all 7 guards
5. Bridge protocol has request + response schemas
6. Space registry template is valid YAML

## Execution Topology
Single worker (MiniMax-M2.7 via delegate_task) — bounded task, no parallelism needed.

## Deliverables
1. ~/.hermes/liaison/README.md
2. ~/.hermes/liaison/policy/guard-policy.md
3. ~/.hermes/liaison/policy/bridge-protocol.md
4. ~/.hermes/liaison/policy/memory-policy.md
5. ~/.hermes/liaison/db/schema.sql
6. ~/.hermes/liaison/schemas/capsule.yaml
7. ~/.hermes/liaison/schemas/fact.yaml
8. ~/.hermes/liaison/schemas/claim.yaml
9. ~/.hermes/liaison/schemas/request.yaml
10. ~/.hermes/liaison/schemas/approval.yaml
11. ~/.hermes/liaison/schemas/task.yaml
12. ~/.hermes/liaison/schemas/digest.yaml
13. ~/.hermes/liaison/schemas/audit-event.yaml
14. ~/.hermes/liaison/schemas/space.yaml
15. ~/.hermes/liaison/schemas/actor.yaml
16. ~/.hermes/liaison/templates/space-registry.yaml
17. ~/.hermes/profiles/public/config.yaml.skeleton
