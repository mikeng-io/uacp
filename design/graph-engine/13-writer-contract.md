---
type: contract
title: Graph Engine — Writer Contract (formatter + validator + entity-level writes)
description: Entity-level engine-mediated writes; the UACP node formatter (canonical form) and validator (reject malformed); agent never touches the filesystem.
tags: [graph-engine, writer, formatter, validator, okf, contract]
timestamp: 2026-06-19
edges:
  - {dst: 11-node-taxonomy, rel: depends_on, provenance: derived}
---

# Writer Contract (contract)

No manifest is written by the coding agent. Every node is created through the **engine**, which owns
serialization end to end. This is the Clean Architecture dependency rule at runtime: the agent talks
to a repository, never the filesystem.

## Entity-level, not path-level

Today's governed writer is path-level and **permissive** — `uacp_artifact_write(path, blob)` writes
whatever YAML it is handed (no schema check). Promote it to entity-level:

```
create_work_unit(run_id, {title, derives_from, body, ...})
```

The engine then, in one transaction:

1. **mints** the id (`wu-2`),
2. runs the **formatter** → canonical OKF form,
3. runs the **validator** → reject if malformed (no write on failure),
4. **writes** `plans/{run_id}/wu-2.md`,
5. **updates** `_index.yaml` (members + edges + coverage),
6. **emits** the edge records for the projection.

The agent supplies *domain data*; it never chooses a path, an id, a key order, or a file layout.

## The UACP formatter (`uacp-fmt`)

A canonical normalizer for UACP OKF nodes — `gofmt`/`black` for manifests. Its job is determinism,
not validity.

- **Frontmatter key order** — fixed canonical order (`kind, id, title, <edges>, status, ...`).
- **Edge serialization shape** — every edge rendered identically as `{src, dst, rel_type, provenance}`
  (or the frontmatter-key shorthand), sorted deterministically.
- **id format** — kind-prefixed, run-scoped, safe-id regex.
- **Body normalization** — trailing whitespace, heading levels, link form.
- **Idempotent** — `fmt(fmt(x)) == fmt(x)`. Stable, minimal diffs; writes are reproducible.

Rationale: a serialization engine needs a *single* on-disk form per logical node, or diffs are noisy,
writes are non-reproducible, and the projection sees spurious churn. The formatter guarantees one
canonical byte-form.

## The UACP validator (`uacp-lint`)

Node-local structural validity — reject before persist (and runnable standalone in CI).

- **Frontmatter** — required fields *per kind* (e.g. `scope_item` needs `id, title`; `work_unit`
  needs `id, title, derives_from`; `assessment` needs `obligation_id, evidence_refs, result`).
- **Edges** — every edge has `{src, dst, rel_type, provenance}`; `provenance` ∈ the enum; `rel_type`
  ∈ the [vocabulary](10-edge-schema.md); endpoints are id-shaped.
- **Kind-specific required edges** — e.g. a `work_unit` MUST carry `derives_from` (this is what
  structurally forbids phantom tasks at the source).
- **OKF frontmatter** — `type, title, description` where the node is also a wiki page.

> **What exists today:** only a partial seed — `tests/unit/skills/test_okf_frontmatter.py`, a *pytest
> lint* scoped to `skills/uacp-core/references/` and `.uacp/knowledge/`, checking `type/title/
> description` presence. It is test-only, not a runtime validator, not manifest-aware, and has no edge
> validation and no formatter. Slice 1 generalizes it into the reusable `uacp-lint` + `uacp-fmt`
> components and wires them into the write path.

## Separation of concerns

- **formatter** — normalizes *shape* (idempotent; never rejects).
- **validator** — rejects *invalid* (never rewrites).
- **closure checks** — cross-node completeness (orphan/phantom/uncovered/...) live in the
  [projection engine](14-projection-engine.md), not here. The writer guarantees each node is
  *well-formed*; the projection guarantees the *graph* is complete.

## Enforcement planes (where these run)

`uacp-fmt`/`uacp-lint` is a **pure capability**, not a plane — it has no policy authority of its own.
Enforcement is split across the two existing gates; they share only the pure-leaf rules:

| Check | Question | Enforced by | When |
|---|---|---|---|
| `uacp-fmt` + `uacp-lint` | is this **node** well-formed / canonical? | **Guardian** | write-time (validate-on-write) |
| projection closure | is the **graph** complete (orphan/phantom/uncovered/...)? | **Heartgate** | phase-exit invariant |

Guardian *invokes* `uacp-lint` on every write; Heartgate *invokes* the projection engine on every
transition. The lint/fmt capability "belongs to Guardian" only in the **invoked-by** sense for the
node-local half — it is not a Guardian submodule, and closure is **Heartgate's, not Guardian's**.
Folding closure into Guardian would collapse the plane separation (Guardian = "is this write
well-formed + contained"; Heartgate = "is the graph complete enough to advance").

### Invocation: library door vs skill door

`uacp-fmt`/`uacp-lint` is **pure deterministic code** — no LLM, no model call. The logic is the
pure-leaf rules module; everything else is a wrapper:

```
pure-leaf rules (Python)          ← the logic; deterministic; single source of truth
  ├─ Guardian              → imports it directly       (runtime enforcement, zero semantic step)
  ├─ Heartgate/projection  → imports it                (closure checks)
  ├─ uacp-lint CLI         → argparse wrapper           (CI / dev / human)
  └─ SKILL.md              → agent-facing discoverability ONLY
```

The **skill is not the execution path** — it is agent-facing discoverability so an agent can run the
tool ad hoc. The enforcement path bypasses it entirely: **gates reach the logic through the library
(an in-process function call); agents reach it through the skill.** "Guardian invokes `uacp-lint`"
means "Guardian calls the leaf function" — never through the skill, an LLM, or an MCP round-trip.
Because the flow is pure-deterministic, no semantic execution is in it.
