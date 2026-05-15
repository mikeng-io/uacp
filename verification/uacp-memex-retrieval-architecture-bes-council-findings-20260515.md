# UACP MEMEX Retrieval Architecture & BES Lens — Council Findings

**Status**: Council Review Complete  
**Date**: 2026-05-15  
**Reviewer**: UACP Architecture Subagent (Agent Council role: retrieval/BES specialist)  
**Scope**: Evaluate proposed UACP MEMEX module retrieval/scoring architecture against Trustless ACP concepts (knowledge RAG, hybrid retrieval, reranker, recall, foresight, BES, pattern_select with BES/domain relevance). Determine: copy Trustless exactly, or adapt/enhance?  
**Artifact**: `verification/uacp-memex-retrieval-architecture-bes-council-findings-20260515.md`

---

## 1. Executive Verdict: CONCERNS (non-blocking) — Adapt/Enhance, Do Not Copy Exactly

| Dimension | Finding |
|-----------|---------|
| **Overall** | **CONCERNS** — UACP MEMEX should adapt Trustless retrieval concepts, not copy them. The current UACP evidence-cluster and memory-policy scaffolding is directionally sound but incomplete. |
| **PASS items** | Evidence cluster registry exists; memory-policy defines storage boundaries; lessons storage path exists; local knowledge locations are declared. |
| **CONCERNS** | No explicit retrieval pipeline defined; no BES formula or effectiveness scoring; no hybrid search or reranker integration; no pattern_select equivalent; knowledge/indexes/ is empty. |
| **BLOCKERS** | None — this is an architecture review, not an implementation gate. |

**Recommendation**: UACP MEMEX should be designed as an **adapted superset** of Trustless retrieval, not a clone. Trustless is spec-centric (findings per spec, pattern recurrence across specs). UACP is run-centric (phase transitions, council synthesis, warnings, deferred items). The retrieval substrate must serve UACP's artifact topology, not Trustless's.

---

## 2. Trustless ACP Retrieval Architecture — Compressed Reference

### 2.1 Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Knowledge RAG** | `.trustless/knowledge/rag.py` | Main query interface: semantic search over verified findings |
| **Storage** | `.trustless/knowledge/storage.py` | ChromaDB + BM25 hybrid index, ingestion tracking |
| **KB Search** | `.trustless/indexer/kb_search.py` | Structured search: tags, invariants, severity, time, file pattern, text |
| **Foresight** | `.trustless/foresight/effectiveness.py` | BES computation, recurrence detection, trend reporting |
| **Effectiveness Scores** | `.trustless/foresight/effectiveness_scores.json` | `{pattern_id: {bes, bonus, eligible, recurrences, status}}` |
| **Pattern Select** | `.agents/skills/lessons/pattern_select.py` | Selects top-N lesson patterns for injection using domain/invariant/file overlap + BES bonus |
| **Lessons Store** | `.trustless/lessons/patterns.jsonl` | Canonical bug-class pattern store |
| **Oracle** | `.trustless/oracle/**` | Phase-scoped projection API assembling context for prompts |

### 2.2 Trustless Retrieval Pipeline

```
Query (error/spec description)
    |
    v
[Hybrid Search] vector similarity (ChromaDB) + BM25 keyword (RRF fusion)
    |
    v
[Re-ranking] cross-encoder reranker (optional, default on)
    |
    v
[Filtering] metadata filters: file_path, spec_id, tags, domain, invariant
    |
    v
[Deduplication] by spec_id (for spec queries)
    |
    v
Results: similar errors / similar specs / patterns for injection
```

### 2.3 Trustless BES Formula

```
BES = (successes + 1) / (eligible + 2) * recency_factor

Where:
  - successes = eligible specs where pattern was NOT recurrent
  - eligible = total later specs sharing domain with pattern
  - recency_factor = 50% decay over 1 year (patterns >2y approach 0.5 prior)
  - Prior (no data) = 0.5

Thresholds:
  - >= 0.70 -> High-effective
  - 0.40–0.69 -> Moderate
  - < 0.40 -> Weak
```

### 2.4 Trustless pattern_select Scoring

```
relevance = intra-spec(+5) + domain_overlap(+1 each) + invariant_overlap(+2 each) + file_match(+3)
total_score = relevance + BES_bonus(1-6, default 3)
min_relevance threshold = 1 (at least one concrete signal required)
```

---

## 3. UACP Current State — Retrieval-Relevant Artifacts

### 3.1 What Exists

| Artifact | Path | Status | Retrieval Relevance |
|----------|------|--------|---------------------|
| Evidence cluster registry | `config/evidence-clusters.yaml` | seed | Defines cluster families but no retrieval pipeline |
| Memory policy | `config/memory-policy.yaml` | seed | Defines storage boundaries |
| Local knowledge locations | `knowledge/scenarios/`, `gate-templates/`, `lessons/`, `indexes/` | partial | `lessons/` has 2 YAML files; `indexes/` is empty |
| State runs | `state/runs/*.yaml` | active | Rich per-run manifests, not indexed |
| Verification artifacts | `verification/*.yaml` | active | 100+ records; not indexed |
| Proposals | `proposals/*.yaml` | active | 20+ proposals; not indexed |
| Plans | `plans/**` | active | Deep hierarchies; not indexed |

### 3.2 What Is Missing

| Missing Component | Trustless Equivalent | Impact |
|-------------------|----------------------|--------|
| Vector embedding store | ChromaDB | No semantic search |
| BM25 keyword index | `storage.py` BM25Okapi | No fast keyword retrieval |
| Hybrid search fusion | `storage.py` `_rrf_fusion()` | No combined ranking |
| Cross-encoder reranker | `rag.py` `reranker` | No relevance re-ranking |
| BES computation | `foresight/effectiveness.py` | No effectiveness scoring |
| Pattern selection logic | `lessons/pattern_select.py` | No automated lesson injection |
| Pattern store (JSONL) | `lessons/patterns.jsonl` | No canonical pattern corpus |
| Oracle projection layer | `.trustless/oracle/**` | No phase-scoped context API |
| Per-run injection tracking | `state/<spec>/injections.jsonl` | No audit trail |

---

## 4. Comparative Analysis: Trustless vs UACP Retrieval Needs

### 4.1 Core Difference in Retrieval Target

| Aspect | Trustless ACP | UACP MEMEX |
|--------|---------------|------------|
| **Primary artifact** | Spec (implementation spec with findings) | Run (governed lifecycle run with phase transitions) |
| **Retrieval unit** | Finding (bug class, root cause, solution) | Phase transition, council synthesis, warning, deferred item, verification outcome, lesson |
| **Temporal scope** | Spec lifecycle | Run lifecycle (triage -> propose -> plan -> execute -> verify -> resolve) |
| **Domain model** | Software implementation | Universal governance (any artifact type, any domain) |
| **Effectiveness target** | Did pattern prevent recurrence in later specs? | Did evidence cluster / lesson improve phase transition quality? |
| **Injection point** | Planning, execution, verification prompts | Triage gate-selection, proposal evidence, plan council shape, execute containment, verify council synthesis |

### 4.2 Why Copying Trustless Exactly Would Be Wrong

1. **Spec-centric vs run-centric**: Trustless indexes `finding_id` + `spec_id`. UACP needs `artifact_id` + `run_id` + `phase` + `cluster_family`.
2. **Pattern type diversity**: Trustless patterns are bug-class patterns. UACP needs multi-type patterns: phase-transition lessons, council synthesis patterns, warning heuristics, deferred-item rationales, verification predictors, skill references, dashboard patterns.
3. **BES target differs**: Trustless BES asks "did this pattern prevent the same bug class from recurring?" UACP BES should ask "did this evidence cluster improve phase transition outcomes or reduce rework?"
4. **Authority boundary**: Trustless retrieval feeds into Oracle, which feeds into prompts. UACP has a stricter authority hierarchy (docs -> config -> state -> skills -> execution). Retrieval must not become a hidden source of truth.
5. **Scale and portability**: Trustless assumes a single large repo with ChromaDB. UACP must be portable across Hermes deployments.

---

## 5. Proposed UACP MEMEX Retrieval Architecture

### 5.1 Architecture Principles (adapted from Trustless)

1. **Retrieval is advisory** — Retrieved context informs gates and councils; it does not approve proposals or trigger state transitions.
2. **Hybrid search by default** — Combine structured filters (phase, domain, risk, artifact type) with semantic similarity.
3. **Re-ranking for council context** — Council synthesis and verification prompts benefit from re-ranked relevance.
4. **BES feedback loop** — Track which retrieved patterns/clusters actually improved outcomes, score them, and prefer high-effectiveness items.
5. **Static index MVP first** — Start with structured YAML/JSON indexes; add embeddings and vector search only when volume justifies it.
6. **Authority/provenance scoring** — Retrieved items must carry provenance (which run, which gate, which council, which verification artifact). Items from verified resolved runs score higher than items from blocked or abandoned runs.

### 5.2 Proposed Retrieval Pipeline

```
User/Agent Query (natural language or structured)
    |
    v
[Query Parser] Extract: phase, domain, risk_level, artifact_type, run_id (optional)
    |
    v
[Structured Filter Layer] Narrow candidate set by metadata
    - phase, domain, risk_level, artifact_type, timestamp range, council_tier
    |
    v
[Semantic Search Layer] (Phase 2+ — optional in Phase 1)
    - Embed query; search over embedded artifact summaries; return top-k
    |
    v
[Hybrid Fusion] (Phase 2+)
    - Reciprocal Rank Fusion of structured-filter rank + semantic rank
    - Alpha weight: 0.7 semantic / 0.3 structured (tunable per domain)
    |
    v
[Re-ranking] (Phase 2+)
    - Cross-encoder or LLM-based re-ranker on fused candidates
    - Prefer items with high authority/provenance scores
    |
    v
[BES-weighted Selection] (Phase 3)
    - Apply BES bonus to ranking
    - Filter out weak patterns (BES < 0.40) unless no alternatives
    |
    v
[Result Assembly]
    - Deduplicate by run_id + artifact_type
    - Attach provenance: source_run, source_phase, source_verification, council_tier
    - Label as `retrieval_hint` (not authority)
    |
    v
[Injection / Context Assembly]
    - Triage: inform gate-selection and evidence cluster choice
    - Propose: inform proposal evidence and risk assessment
    - Plan: inform council shape and verification strategy
    - Verify: inform council synthesis and finding context
    - Resolve: inform lesson extraction and memory policy
```

### 5.3 Proposed BES Formula for UACP

**Name**: `uacp_bes` (Bayesian Effectiveness Score for UACP patterns/clusters)

**Formula**:

```
uacp_bes = (successes + 1) / (eligible + 2) * recency_factor * authority_factor

Where:
  - successes = eligible later runs where pattern/cluster was injected
                AND phase transition outcome improved (or stayed pass)
                AND no recurrence of the same warning/deferred item
  - eligible = total later runs sharing domain + phase context with pattern
  - recency_factor = same as Trustless: 50% decay over 1 year
  - authority_factor = provenance multiplier:
      - 1.0 -> pattern from verified resolved run with council review
      - 0.8 -> pattern from verified run but no council
      - 0.6 -> pattern from blocked/abandoned run (still learnable but lower confidence)
      - 0.5 -> pattern from pre-tracking era (no injection audit trail)

Prior (no data) = 0.5

Thresholds (same as Trustless):
  - >= 0.70 -> High-effective
  - 0.40–0.69 -> Moderate
  - < 0.40 -> Weak (candidate for retirement or refinement)
```

**Additional Fields** (per pattern/cluster record):

```yaml
pattern_id: "UP-001"  # UACP Pattern (not LP like Trustless)
kind: "evidence_cluster" | "lesson" | "warning_heuristic" | "council_synthesis_pattern" | "deferred_rationale" | "verification_predictor"
domains: ["governance", "hermes-agent"]
phases: ["plan", "verify"]
source_run_id: "uacp-phase5-kanban-guard-20260514"
source_phase: "verify"
source_council_tier: "local"
source_verification_artifact: "verification/uacp-phase5-kanban-guard-verify-20260514.yaml"
invariants: ["authority", "traceable_state"]
affected_artifact_types: ["config", "plan"]
affected_cluster_families: ["write_containment", "risk"]
description: "..."
prohibition: "..."
prevention: "..."
bes: 0.725
bonus: 5
eligible: 12
recurrences: 2
status: "RECURRING" | "PREVENTED" | "NO_DATA"
authority_factor: 1.0
injection_history:
  - run_id: "..."
    phase: "plan"
    outcome: "pass"
    injected_at: "2026-05-14T12:00:00Z"
```

### 5.4 Proposed pattern_select Equivalent for UACP

**Name**: `uacp_select_patterns` (or skill: `uacp-memex-select`)

**Scoring**:

```
relevance = intra-run(+5) + domain_overlap(+1 each) + phase_overlap(+2 each)
            + invariant_overlap(+2 each) + artifact_type_match(+2 each)
            + cluster_family_match(+1 each) + risk_level_match(+1)

total_score = relevance + BES_bonus(1-6, default 3) + authority_bonus(0-2)

Where:
  - intra-run: +5 if pattern extracted from same run (highest signal)
  - domain_overlap: +1 per matching domain
  - phase_overlap: +2 per matching phase (stronger than domain for UACP)
  - invariant_overlap: +2 per matching invariant
  - artifact_type_match: +2 if current task's artifact type matches pattern's
  - cluster_family_match: +1 per matching evidence cluster family
  - risk_level_match: +1 if risk levels align
  - BES_bonus: from effectiveness_scores (default 3 for unscored)
  - authority_bonus: +2 if authority_factor=1.0, +1 if 0.8, 0 otherwise

min_relevance threshold = 1 (at least one concrete signal)
hard_limit = configurable (default 10)
```

**Selection Modes**:

1. **By domain index** — Read pre-built `knowledge/by-domain/<domain>.yaml`
2. **By phase index** — Read pre-built `knowledge/by-phase/<phase>.yaml`
3. **By invariant index** — Read pre-built `knowledge/by-invariant/<inv>.yaml`
4. **Score and select** — Full relevance + BES ranking

---

## 6. Implementation Phases

### Phase 1: Static Index MVP (Week 1-2)

**Goal**: Structured retrieval without embeddings — immediate value, minimal dependencies.

**Deliverables**:
- [ ] `knowledge/indexes/patterns.jsonl` — canonical UACP pattern store (append-only)
- [ ] `knowledge/indexes/effectiveness_scores.json` — BES scores (initially empty, seeded with 0.5 prior)
- [ ] `knowledge/by-domain/*.yaml` — domain-indexed pattern summaries
- [ ] `knowledge/by-phase/*.yaml` — phase-indexed pattern summaries
- [ ] `knowledge/by-invariant/*.yaml` — invariant-indexed pattern summaries
- [ ] `scripts/uacp_select_patterns.py` — pattern selection tool (structured filters only, no embeddings)
- [ ] `config/memex.yaml` — MEMEX configuration (index paths, BES parameters, selection thresholds)

**Retrieval capability**:
- Structured search: phase, domain, risk, artifact type, invariant, timestamp
- Keyword search over pattern descriptions (simple substring or regex)
- No vector search, no hybrid fusion, no reranker

**BES**:
- Formula implemented but scores are all 0.5 (prior) until enough runs accumulate

---

### Phase 2: Hybrid Search + Re-ranking (Week 3-5)

**Goal**: Add semantic search and re-ranking when pattern volume > 100 or when structured search quality degrades.

**Deliverables**:
- [ ] Embedding generator (lightweight: sentence-transformers/all-MiniLM-L6-v2 or API equivalent)
- [ ] Vector store integration (ChromaDB, SQLite-vec, or pgvector if service-backed)
- [ ] BM25 keyword index over pattern descriptions
- [ ] RRF hybrid fusion (vector + structured-filter rank + BM25)
- [ ] Cross-encoder or LLM-based re-ranker
- [ ] Update `uacp_select_patterns.py` to support `--use-hybrid` and `--use-rerank`

---

### Phase 3: BES Outcome Feedback + Authority/Provenance Scoring (Week 5-7)

**Goal**: Close the feedback loop — track which patterns improved outcomes and score them.

**Deliverables**:
- [ ] `scripts/uacp_compute_bes.py` — BES computation with recency decay and authority factor
- [ ] Per-run injection tracking: `state/runs/<run-id>/injections.jsonl`
- [ ] Recurrence detection: compare current run warnings/deferred items against injected patterns
- [ ] Effectiveness report generation (weekly or per-run)
- [ ] SLO monitoring: F/run (findings per run), BES distribution, recurrence rate
- [ ] Auto-retirement of weak patterns (BES < 0.40 after 10+ eligible runs)

---

### Phase 4: Oracle Projection Layer + Council Integration (Week 7-9)

**Goal**: Phase-scoped context assembly for council prompts — the MEMEX becomes a runtime API.

**Deliverables**:
- [ ] `uacp-oracle` skill / module — assembles context for a given phase + run
- [ ] Integration with `uacp-triage` — retrieve similar past triage decisions
- [ ] Integration with `uacp-propose` — retrieve relevant proposal evidence patterns
- [ ] Integration with `uacp-plan` — retrieve plan council shapes and verification strategies
- [ ] Integration with `uacp-verify` — retrieve council synthesis patterns and warning heuristics
- [ ] Integration with `uacp-resolve` — retrieve lesson extraction patterns

---

### Phase 5: Knowledge Bank Service Extraction (Future — deferred)

**Goal**: When UACP scales beyond single-Hermes deployment, extract MEMEX into a standalone service.

**Trigger**: > 1000 patterns, > 100 runs/month, or multi-runtime deployment.

**Deliverables**:
- [ ] Standalone Knowledge Bank API (REST or MCP)
- [ ] Shared across multiple Hermes / UACP instances
- [ ] Honcho integration for operator preferences (read-only, not sole owner)
- [ ] Cortex integration for editorial/workflow consumption

---

## 7. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Retrieval becomes hidden authority | HIGH | Explicit `retrieval_hint` labeling; retrieval never overrides docs/config/state |
| BES scores gamed or misleading | MEDIUM | Authority factor penalizes low-confidence sources; manual review of high-recurrence patterns |
| Pattern volume stays low; BES never converges | LOW | Prior of 0.5 is safe default; structured search works without BES |
| Embedding dependencies bloat UACP | MEDIUM | Phase 1 is embedding-free; Phase 2 uses lightweight models; service extraction deferred |
| Council treats retrieved patterns as normative | HIGH | Injection labeling; constitution explicitly states retrieval is advisory |
| Duplicate Trustless anti-patterns | MEDIUM | This review explicitly rejects clone approach; adapted architecture is run-centric |

---

## 8. Council Recommendation Summary

1. **Do NOT copy Trustless exactly**. Adapt retrieval concepts to UACP's run-centric, universal-governance model.

2. **Start with static structured indexes (Phase 1)**. UACP currently has ~20 runs and sparse lessons — embeddings are premature overhead.

3. **Define the UACP BES formula now** (Section 5.3). Even with prior-only scores, the formula shapes future data collection.

4. **Build `uacp_select_patterns` as a skill/script** (Section 5.4). It replaces Trustless `pattern_select.py` with UACP-relevant signals.

5. **Keep retrieval advisory** (Section 5.1, Principle 1). The Knowledge Boundaries doc from Trustless applies directly: retrieval informs; it does not decide.

6. **Defer Knowledge Bank service** (Phase 5). Local knowledge under `UACP_ROOT/knowledge/` is sufficient for Stage 1-3.

7. **Integrate MEMEX into lifecycle skills incrementally** (Phase 4). Start with `uacp-verify` (council synthesis context) and `uacp-triage` (gate-selection evidence).

---

## 9. Cross-References

- Trustless ACP knowledge boundaries: `workspace/trustless/.trustless/docs/control-plane/knowledge-boundaries.md`
- Trustless foresight metrics: `workspace/trustless/.trustless/docs/control-plane/foresight-metrics.md`
- Trustless RAG implementation: `workspace/trustless/.trustless/knowledge/rag.py`
- Trustless pattern select: `workspace/trustless/.agents/skills/lessons/pattern_select.py`
- UACP memory policy: `config/memory-policy.yaml`
- UACP evidence clusters: `config/evidence-clusters.yaml`
- UACP document registry: `docs/index.md`

---

*End of Council Findings*
