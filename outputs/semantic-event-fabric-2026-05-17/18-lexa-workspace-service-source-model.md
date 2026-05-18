# Addendum: LEXA Workspace and Service Grouping Model

Date: 2026-05-17
Status: architectural refinement

## Question

How should LEXA group consumer services and state boundaries?

Mike's requirement:

```text
Each service owns canonical state.
LEXA provides API server + SDK + derived index/query layer.
State database must be elastic and durable.
```

## Recommendation

Use a three-level grouping model:

```text
Workspace -> Service -> Source
```

Where:

- **Workspace** is the top-level trust/tenant/security boundary.
- **Service** is an owning system inside a workspace.
- **Source** is a specific retrievable collection/indexable corpus exposed by a service.

## Definitions

### Workspace

A workspace is a trust and tenancy boundary.

Examples:

- `nortrix`
- `uacp`
- `trustless`
- `cortex`
- `nora-public`
- `norty-private`

A workspace defines:

- access policy;
- privacy class defaults;
- allowed clients;
- index namespaces;
- retention defaults;
- audit scope;
- encryption/backup boundaries;
- cross-service query permissions.

### Service

A service is a canonical state owner.

Examples:

- `uacp-memex`
- `sef`
- `cortex-editorial`
- `trustless-acp`
- `hermes-memory`
- `nora-profile`

A service defines:

- source adapters;
- canonical state location/API;
- indexing mode: pull/push/embedded;
- freshness rules;
- BES/ranking features if any;
- source-local authorization.

### Source

A source is a retrievable/indexable corpus or stream owned by a service.

Examples:

- `uacp.memex.evidence`
- `uacp.memex.patterns`
- `sef.events`
- `sef.graph_snapshots`
- `cortex.articles`
- `cortex.recall_packets`
- `trustless.control_plane_docs`
- `trustless.evolution`
- `hermes.sessions`

A source defines:

- schema;
- chunking strategy;
- index backend;
- query modes;
- metadata filters;
- privacy labels;
- rebuild manifest;
- source version/hash tracking.

## Canonical ID shape

Use stable hierarchical IDs:

```text
workspace:<workspace_id>
service:<workspace_id>/<service_id>
source:<workspace_id>/<service_id>/<source_id>
item:<workspace_id>/<service_id>/<source_id>/<item_id>
chunk:<workspace_id>/<service_id>/<source_id>/<item_id>#<chunk_id>
```

Example:

```text
workspace:nortrix
service:nortrix/uacp-memex
source:nortrix/uacp-memex/evidence
item:nortrix/uacp-memex/evidence/proposal-123
chunk:nortrix/uacp-memex/evidence/proposal-123#chunk-004
```

## Query scoping

A LEXA query should declare scope explicitly:

```yaml
workspace: nortrix
client: sef-resolver
query: 飯局 group Wednesday dinner
sources:
  - nortrix/sef/events
  - nortrix/sef/graph_snapshots
  - nortrix/uacp-memex/patterns
privacy_view: norty_private
modes:
  - keyword
  - semantic
  - rerank
features:
  use_bes: true
```

The server must reject queries that cross workspace/service/source boundaries without explicit policy.

## Derived index partitioning

LEXA derived indexes should be partitioned by:

```text
workspace_id
service_id
source_id
privacy_view
index_backend
schema_version
```

This gives elasticity and prevents accidental cross-contamination between private/public profiles or unrelated projects.

## Access control model

Authorization should be evaluated at multiple layers:

1. Workspace access: can this client query this workspace?
2. Service access: can this client access this service's sources?
3. Source access: can this client query this corpus?
4. Item/chunk visibility: do privacy labels allow this result to appear?
5. Feature access: may this client see BES scores, raw evidence, snippets, or only redacted summaries?

## Source-owned state invariant

The workspace/service/source hierarchy describes access and derived index ownership. It does not transfer canonical state ownership.

```text
Canonical state owner = service.
Derived index owner = LEXA deployment namespace for that service/source.
Query access = workspace/service/source policy.
```

## Deployment shapes

### Single LEXA server, multiple workspaces

Good for Nortrix homelab/private deployment. Requires strict workspace isolation.

### One LEXA server per workspace

Good when trust boundaries are strong, e.g. public Nora vs private Norty.

### Embedded LEXA SDK per service

Good for isolated or early-stage services. Can later graduate to server mode.

## Recommendation for first implementation

Start with one LEXA server that supports multiple workspaces, but configure only a narrow `nortrix` private workspace first.

Do not onboard public Nora data until workspace/service/source isolation and privacy tests pass.

## Invariant

```text
Workspace = trust boundary.
Service = canonical state owner.
Source = retrievable corpus.
LEXA index = derived, partitioned, rebuildable view.
```
