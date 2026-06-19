---
type: pattern
title: Graph Engine — Operational Flows (read / write / transition / rebuild)
description: "Operation sequences (write / lookup / transition / rebuild) with Mermaid diagrams. SUPERSEDED in part by D29: the single-SQLite framing is historical; CURRENT structure store = plain YAML + in-memory projection (no DB). The flow shapes still apply."
tags: [graph-engine, flows, read, write, operations, mermaid]
timestamp: 2026-06-20
edges:
  - {dst: 14-projection-engine, rel: depends_on, provenance: derived}
---

# Operational Flows (the drill)

> ⚠️ **SUPERSEDED in part by D29 (final-review T1).** The flow *shapes* (write/lookup/transition/rebuild,
> CRUD, end-to-end trace) are current — but every mention of "one SQLite (sqlite-vec + FTS5)" / the Index
> engine is **historical single-DB framing**. In v1 the structural store is **plain YAML files + an
> in-memory projection (no database)**; the "Index engine" is just the in-memory projector. See D29/D20.

One line: **agents read/write *files* through validated governed calls; one SQLite index (edges +
sqlite-vec + FTS5), reached only via the Index engine, makes lookup fast; git versions the files; the
DB rebuilds from them.**

> **Diagram legend.** In the graph walks, **arrows show traversal direction** and the `(rel)` label is
> the stored edge key. Foreign keys are physically stored **child → parent** (`wu --derives_from--> si`,
> `cp --work_unit_id--> wu`); the recursive CTE walks them in **either** direction (ascend or descend).
> **`DB` is one SQLite** holding edges + `sqlite-vec` vectors + `FTS5` — exact walk and fuzzy search hit
> the *same* file; the **Index engine** is the only thing that touches it (D14/D16). The Index engine
> (the wrapper) is **defined** in [14-projection-engine](14-projection-engine.md); these flows only
> **use** it — single source, they don't redefine it.

---

## 1. WRITE — create/update a node

```mermaid
sequenceDiagram
    autonumber
    actor Agent
    participant W as Entity Writer
    participant F as uacp-fmt
    participant L as uacp-lint
    participant S as uacp-schema
    participant G as Guardian
    participant FS as Files (git truth)
    participant IX as Index engine
    participant DB as SQLite (one DB)
    Agent->>W: create_work_unit(run, {title, derives_from, body})
    W->>W: mint id (wu-2), assemble OKF node
    W->>F: normalize
    F-->>W: canonical node
    W->>L: validate
    L->>S: enums / closed-world / required edges
    S-->>L: ok or violations
    alt invalid
        L-->>Agent: REJECT (no write)
    else valid
        W->>G: request write
        G-->>W: allow (root / containment / policy)
        W->>FS: write wu-2.md + update _index.yaml
        FS-->>W: committed (git-trackable truth)
        W->>IX: notify changed file
        IX->>DB: upsert edges + embed text → sqlite-vec (one ACID txn)
    end
```

The agent supplies domain data only — never a path, id, or DB row.

---

## 2. READ (forward) — fuzzy concept → structure (multi-hop descend)

One SQLite serves both steps; the Index engine resolves (sqlite-vec) then walks (CTE):

```mermaid
sequenceDiagram
    autonumber
    actor U as Caller
    participant IX as Index engine
    participant DB as SQLite (edges + sqlite-vec + FTS5)
    participant FS as Files
    U->>IX: lookup("how does login work?")
    IX->>DB: resolve — sqlite-vec nearest-neighbor
    DB-->>IX: entry node = si-1 (semantic step)
    IX->>DB: walk(si-1, hard edges) — recursive CTE
    DB-->>IX: subgraph ids
    IX->>FS: load node files
    FS-->>U: full subgraph (truth)
```

The vector resolve is the **only** semantic step; the walk is exact — and both are the same DB.

The multi-hop walk it returns:

```mermaid
flowchart LR
    Q(["query: 'login'"]) -. fuzzy .-> SI1
    SI1["si-1 · scope_item (intent)"] -- "(derives_from)" --> WU1["wu-1 · provider config"]
    SI1 -- "(derives_from)" --> WU2["wu-2 · token endpoint"]
    WU2 -- "(obligation_for)" --> EV1["ev-1 · obligation"]
    WU2 -- "(work_unit_id)" --> CP2["cp-2 · checkpoint"]
    CP2 -- "(code_anchor)" --> FN["login() @ auth/oauth.py:48"]
    EV1 -- "(evidence_refs)" --> AS1["as-1 · assessment = pass"]
```

---

## 3. READ (reverse) — task/code → intent (multi-hop ascend, no search)

```mermaid
flowchart LR
    FN["login() symbol"] -- "(code_anchor)" --> CP2["cp-2 · checkpoint"]
    CP2 -- "(work_unit_id)" --> WU2["wu-2 · token endpoint"]
    WU2 -- "(derives_from)" --> SI1["si-1 · scope_item"]
    SI1 -- "(in proposal)" --> INT(["intent: OAuth login"])
    AS1["as-1 · assessment"] -- "(work_unit_id)" --> WU2
```

Pure FK walk over the one SQLite — no vector step at all. Filter `provenance` for hard-only (proven)
vs include inferred (advisory). v1 returns the subgraph + provenances; it does **not** synthesize.

---

## 4. TRANSITION — e.g. PLAN → EXECUTE

```mermaid
sequenceDiagram
    autonumber
    actor Agent
    participant H as Heartgate
    participant IX as Index engine
    participant DB as SQLite
    participant C as Council (PROPOSE→PLAN only)
    participant FS as Files
    Agent->>H: request PLAN→EXECUTE
    H->>IX: closure queries
    IX->>DB: orphan / phantom / uncovered / unverified
    DB-->>IX: results
    IX-->>H: findings
    opt PROPOSE→PLAN seam
        H->>C: semantic review (is decomposition right?)
        C-->>H: pass / concerns
    end
    alt all pass
        H->>FS: write phase_transition node (git)
        H-->>Agent: PASS
    else any fail
        H-->>Agent: BLOCK (which check)
    end
```

Two gates only meet at PROPOSE→PLAN: structural closure (Heartgate, over the DB) **and** judgment (council).

---

## 5. REBUILD — fresh clone / lost index

```mermaid
flowchart TD
    GC([git clone]) --> FS["Files = truth (OKF/YAML)"]
    FS --> P[Projector]
    FS --> SCIP[SCIP indexer]
    P -- "parse nodes + _index.yaml; embed text" --> DB[("ONE SQLite: edges + sqlite-vec + FTS5")]
    SCIP -- "defines / references / calls" --> DB
    DB -. "watermark = commit" .-> DONE([index ready])
```

One DB to rebuild; nothing is lost — the index was never a record.

---

## 6. CODE-PLANE (Slice 2) — connecting reality

```mermaid
flowchart LR
    REPO[("repo")] --> SCIP[SCIP]
    SCIP --> CS1["login() symbol"]
    CS1 -- "(calls)" --> CS2["verifyPassword()"]
    CS1 -- "(calls)" --> CS3["issueJWT()"]
    EXEC["EXECUTE checkpoint cp-2"] -- "code_anchor (parsed)" --> CS1
    WU2["wu-2"] -. "(work_unit_id ascend)" .- EXEC
    SI1["si-1 intent"] -. "(derives_from ascend)" .- WU2
```

SCIP's symbol nodes + edges land in the **same** SQLite as the manifest edges. Once the checkpoint
records `code_anchor`, the reverse drill runs end to end: `login()` → cp-2 → wu-2 → si-1 → intent.

---

## 7. EDIT — update in place (same id)

```mermaid
sequenceDiagram
    autonumber
    actor Agent
    participant ME as Manifest engine
    participant MW as Index engine (middleware)
    participant FS as Files (git)
    participant DB as SQLite
    Agent->>ME: edit(wu-2, {new body / re-point derives_from})
    ME->>ME: fmt + lint(schema) — SAME id
    ME->>FS: rewrite wu-2.md (git diff shows exact change)
    ME->>MW: changed(wu-2)
    MW->>DB: re-sync node + edges; re-embed text
    MW->>DB: closure re-check (did the edit orphan anything?)
    DB-->>MW: ok / findings
```

Identity is preserved → inbound edges (`cp-2 → wu-2`) stay valid. Only the node's own content/outbound
edges change; the middleware re-syncs and re-checks closure.

## 8. DELETE — tombstone, never silent orphaning

```mermaid
sequenceDiagram
    autonumber
    actor Agent
    participant ME as Manifest engine
    participant MW as Index engine (middleware)
    participant DB as SQLite
    participant FS as Files
    Agent->>ME: delete(wu-2)
    ME->>MW: dependents of wu-2?
    MW->>DB: query inbound edges
    DB-->>MW: [cp-2 work_unit_id]
    alt has dependents
        MW-->>Agent: BLOCK — would orphan cp-2 (tombstone or re-point first)
    else none
        ME->>FS: set status: deleted (tombstone, kept for audit)
        ME->>MW: changed(wu-2)
        MW->>DB: mark rows retired
    end
```

Hard-delete of a node with dependents is **blocked** by closure (it would create phantoms). Default is a
**tombstone** (`status: deleted`, retained) — git keeps history regardless.

## 9. SUPERSEDE — replace with lineage

```mermaid
flowchart LR
    SI1["si-1 (status: superseded)"] -- "superseded_by (asserted)" --> SI1b["si-1b (active)"]
    SI1b -- "supersedes" --> SI1
    WU2["wu-2"] -. "re-point derives_from → si-1b" .-> SI1b
```
```mermaid
sequenceDiagram
    autonumber
    actor Agent
    participant ME as Manifest engine
    participant MW as Index engine (middleware)
    participant FS as Files
    Agent->>ME: supersede(si-1 → si-1b)
    ME->>FS: create si-1b (active); si-1 status=superseded; add supersedes / superseded_by
    ME->>FS: re-point children (derives_from si-1 → si-1b)
    ME->>MW: changed(si-1, si-1b, children)
    MW->>MW: closure — no dangling refs to si-1; lineage intact
```

The old node is **kept** (not destroyed) and the supersession is a first-class, queryable fact —
"what replaced si-1, and why" is just a `supersedes` edge walk. (See [02-decisions](02-decisions.md) D18.)

## Consistency

The one SQLite carries a **source watermark** (commit/content hash). Stale → rebuild. One ACID store →
**no cross-store transaction** (D16); truth is the files. (See [19-storage-summary](19-storage-summary.md), [02-decisions](02-decisions.md) D13/D16.)
