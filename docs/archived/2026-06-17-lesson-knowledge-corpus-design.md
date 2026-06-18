# Lesson & Knowledge Corpus + Distillation Loop — Design

> Design doc B of three. A = brainstorm phase · **B = this** · C = Oracle retrieval engine.
> This is the *data model + lifecycle* the Oracle (Doc C) reads and writes. Ship before/with C.

**Goal:** Define UACP's two prior-art corpora — **lessons** (empirical, per-run) and **knowledge** (distilled, general) — their format, on-disk location, tagging, multi-project scoping, effectiveness scoring (BES), and the **lesson → knowledge distillation loop**. Today neither is produced or retrieved in a governed, scalable way.

**Status:** Approved in brainstorming dialogue 2026-06-17.

---

## Lesson vs. knowledge — the distinction

They are the **same file format, different producer / shape / ranking / scope.**

| | **Lesson** | **Knowledge** |
|---|---|---|
| One-liner | "In run R, doing X caused failure F — don't." | "Here's how to do X well / how Y works." |
| Nature | particular, empirical, **negative**, dated | general, synthesized, **constructive** |
| Source | **extracted at RESOLVE** from gate/verification findings | **distilled** from recurring lessons **+** design **+** research |
| Measured? | **yes — BES** (recurrence-tracked) | no |
| Scope | **project-local** | **cross-project shareable** |
| Producer | one phase (RESOLVE) | accretes (promotion + top-down authoring) |

Relationship: **lessons are data points; knowledge is the theory built from them** (plus design and research). Promotion (lesson → knowledge) is also a **scope-widening** (project-local → shareable).

## Format — one OKF doc per item

Each lesson and each knowledge item is a single **OKF markdown file** (frontmatter + prose body) — same convention as `docs/knowledge/`, extended with retrieval/effectiveness fields. This kills the monolithic `patterns.jsonl` (which doesn't scale, has merge contention, and has no project dimension) and makes the prose body directly embeddable.

**Lesson frontmatter (`.uacp/lessons/<id>.md`):**
```yaml
type: lesson
id: <stable-id>
title: <human title>
project: <project key>          # multi-project scoping
domains: [<domain>, ...]        # deterministic overlap retrieval
invariants: [<invariant id>, ...]
affected_paths: [<glob>, ...]
severity: CRITICAL|HIGH|MEDIUM|LOW
source_run: <run_id>            # provenance
extracted_at: <ISO ts>
# BES (recomputed, not hand-set):
eligible: <int>
recurrences: <int>
bes: <0..1>
promoted_to: <knowledge-id>     # backlink, set when promoted
tags: [...]
```
Body: `description` / `prohibition` / `prevention` prose (the semantic payload).

**Knowledge frontmatter (`.uacp/knowledge/<id>.md`):** OKF `type ∈ {pattern, digest, analysis, contract}` (no `lesson`), `title`, `description`, `tags`, `domains`, `project|shared`, `derived_from: [<lesson-id>...]` (provenance for bottom-up), `timestamp`. No BES.

## Locations — `.uacp/`, tracked (the `.gitignore` already decided this)

The existing `.gitignore` encodes the runtime/durable split:
```
# per-phase run dirs are runtime; ... knowledge/ (project-learned) are project-level and tracked.
.uacp/state/  .uacp/proposals/  .uacp/plans/  .uacp/executions/
.uacp/verification/  .uacp/resolutions/  .uacp/bridges/  .uacp/councils/
```
The per-phase run dirs are **gitignored (ephemeral)**; `.uacp/knowledge/` is **tracked (durable, project-level)**. So:

| Corpus | Path | Tracked? |
|---|---|---|
| Lessons | `.uacp/lessons/<id>.md` (shardable by `project`/`domain`) | tracked |
| Knowledge | `.uacp/knowledge/<id>.md` | tracked |
| Derived index | `.uacp/knowledge/indexes/` | gitignored (rebuildable) — Doc C |

**Durability needs no `docs/`.** `.uacp/knowledge/` is already committed, so knowledge is permanent without living in `docs/`. (`docs/knowledge/` remains UACP's *own development* knowledge bank — a separate scope, not the runtime governed-project store.)

**Migration:** the current top-level `knowledge/lessons/*.yaml` + `knowledge/*.md` (tracked today) and `config/uacp.toml [memory.local_knowledge_locations]` (which points `lessons`/`indexes` under `knowledge/`) realign to `.uacp/lessons/` + `.uacp/knowledge/` + `.uacp/knowledge/indexes/`. One-time move + config repoint.

## Multi-project

Trustless ACP governs one repo; UACP may govern many — so the corpora are **project-partitioned**:
- **Lessons are project-local** (a bug in Project A is not Project B's lesson). Scoped by the project's `.uacp/` namespace + `project` frontmatter tag; the Oracle defaults to the current project.
- **Knowledge can be cross-project** (a generalizable pattern transcends one repo) — marked `shared`. Promotion widens scope from project-local lesson to shared knowledge.
- Oracle queries *this project's lessons* + *shared knowledge*, with optional cross-project lesson recall on request (Doc C).

## BES — effectiveness score (ported from Trustless ACP)

Ranks lessons by "has this bug class actually stayed prevented." **Gates on concrete relevance; BES only ranks.**

```
if eligible == 0:  BES = 0.5                       # prior (no data)
successes = eligible − recurrences
smoothed  = (successes + 1) / (eligible + 2)        # Beta(1,1) posterior mean
recency   = max(0.5, 1 − 0.5 · days_since_extracted/365)
BES       = smoothed × recency
```
- *eligible* = later resolved runs sharing ≥1 domain, started after the lesson; *recurrence* = a later run with a finding matching the **same invariant AND domain**.
- BES → ranking bonus (5 tiers: ≥.85→5, ≥.70→4, ≥.55→3, ≥.40→2, else→1; +1 if CRITICAL/HIGH; −2 if BES<.4 & eligible≥5).
- Retrieval (Doc C): `relevance = intra-run(+5) + domain(+1·n) + invariant(+2·n) + path(+3)`, **gate** `relevance ≥ 1`, then **rank** by `relevance + bes_bonus`. Recurrence (and thus BES) is **recomputed at RESOLVE** over the project's resolved runs.

## The distillation loop (lesson → knowledge)

**Trigger — cross-run evidence, BES-gated.** A lesson stays a lesson when seen once; it becomes a *promotion candidate* when evidence shows it **generalizes**:
- **Consistently effective:** `bes ≥ threshold AND eligible ≥ N` → "reliably works" → positive pattern.
- **Chronically recurring:** recurs across `≥ K` distinct runs/domains → "keeps biting us" → strong prohibition/principle.

Evaluated at **RESOLVE** (after lessons written + BES recomputed) and in an explicit/periodic `distill` maintenance pass. Reuses BES data — no new effectiveness machinery.

**Mechanism — council synthesis, extend-over-create.** When a candidate fires:
1. Gather the **cluster of related lessons** (same class/domain/invariant) + **existing knowledge docs on the topic** (retrieved via the Oracle itself — Doc C) + relevant design rationale.
2. Dispatch an **Agent Council synthesis** to abstract them into a generalized pattern/principle (when it applies, how to satisfy it) — divorced from the specific runs.
3. **Extend-over-create:** if a knowledge doc owns the topic, **update** it (merge new evidence/nuance); else create one. (Same anti-proliferation rule as the reference-doc policy.) This *is* the "integrating existing documents" step.
4. Write via governed writer to `.uacp/knowledge/`; set `derived_from`/`promoted_to` backlinks.

**Top-down intake.** Knowledge also arrives without a lesson behind it: **design** (ADR digests) and **research/analysis** (council research mode, studying other systems) author knowledge docs directly. So `.uacp/knowledge/` has two intake paths — bottom-up promotion (recurrence-gated) and top-down authoring.

## Producer / consumer summary

- **RESOLVE** extracts lessons → `.uacp/lessons/`; recomputes BES; runs the promotion check.
- **Distillation** (RESOLVE-adjacent or periodic) promotes lessons → `.uacp/knowledge/` via council synthesis.
- **Oracle (Doc C)** retrieves both at the decision phases (brainstorm/triage advisory; propose/plan/verify retrieval-led); does **not** write them.

## Open items

- **Promotion thresholds** (`N` eligible, `K` runs, BES cutoffs) — start conservative, tune.
- **Lesson extraction quality** — clustering of raw findings into bug classes (Trustless ACP uses an LLM pre-cluster step); decide council vs single-agent.
- **Cross-project `shared` knowledge store location** — a per-project `.uacp/knowledge/` holds project knowledge; a *shared* tier (across projects) needs a home (e.g. a user-level UACP knowledge dir). Defer until multi-project is exercised.
- **Idempotency** of extraction/promotion (markers, dedup) — port Trustless ACP's `.extract_markers/` idea.
