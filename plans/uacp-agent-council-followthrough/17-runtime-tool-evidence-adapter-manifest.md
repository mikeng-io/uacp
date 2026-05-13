# 17 — Runtime / Tool / Evidence Adapter Manifest

Status: design-complete

## Purpose

Define the minimum manifest shape for surfaces allowed in UACP EXECUTE/VERIFY.

## Adapter classes

- `agent_runtime`: hosts autonomous or semi-autonomous cognition/execution loops.
- `tool_adapter`: acts or observes under direct worker control, but does not host independent agent cognition.
- `evidence_service`: retrieves/processes evidence and returns artifacts.
- `control_substrate`: stores/coordinates tasks, comments, dependencies, status, and provenance.

## Manifest schema

```yaml
kind: uacp.adapter_manifest
schema_version: "0.1"
adapter_id: "..."
class: agent_runtime | tool_adapter | evidence_service | control_substrate
provider: "..."
capabilities: []
authority_requirements:
  requires_uacp_context: true
  protected_actions: []
side_effect_profile:
  reads: []
  writes: []
  external_visibility: none | internal | external | public
  reversibility: reversible | partially_reversible | irreversible
provenance:
  required_fields: [runtime, adapter, actor, task_id, timestamp, artifact_paths]
audit:
  required: true
  audit_artifact: "verification/...yaml"
failure_policy:
  missing_context: block
  unknown_side_effect: block
  timeout: block_or_retry_once
```

## Initial examples

- Hermes: `agent_runtime`, primary host/runtime, requires Guardian/Heartgate context for protected actions.
- Claude Code / Codex / OpenCode / Kimi / Gemini: `agent_runtime`, external runtime adapter when scale, complexity, independent perspective, or runtime need justifies it.
- Browser/computer-use/terminal/local scripts/OCR: `tool_adapter`, requires explicit side-effect and containment classification.
- Firecrawl/Tavily/SearXNG/web search/transcripts: `evidence_service`, network-read/evidence boundary; does not create authority.
- Hermes Kanban: `control_substrate`, current coordination adapter; stores task graph and provenance but does not own phase state.

## Admission rule

No adapter may be used for UACP protected work unless its manifest states class, authority requirements, side-effect profile, provenance fields, audit requirements, and failure policy.
