---
type: contract
title: RESOLVE lesson OKF extraction, BES recompute, and distillation
description: Operational procedure for extracting durable lessons to .uacp/lessons/, recomputing BES, and promoting lessons to .uacp/knowledge/ at RESOLVE time.
tags: [resolve, lessons, knowledge, corpus, bes, distillation]
timestamp: "2026-06-17"
---

## Purpose

After RESOLVE writes `resolutions/{run_id}-lessons.yaml` (the gate artifact), durable lessons are extracted as OKF markdown files into `.uacp/lessons/<id>.md` and scored for effectiveness. High-scoring or chronically-recurring lessons are promoted to `.uacp/knowledge/`.

All corpus writes go through the **Oracle corpus-write surface**. A tool-surface-only agent persists via the governed **`uacp_corpus_write`** tool (`kind: lesson|knowledge`, `okf: <the OKF markdown>`) — the tool delegates to the Oracle's `write_corpus` entrypoint, which validates the OKF and routes it through the governed artifact writer (Guardian-audited; `lessons/` and `knowledge/` are in scope per `config/uacp.toml [scope.tool_path_capabilities]`). The Oracle is the single owner of the knowledge/lesson corpus (read *and* write); RESOLVE never calls `uacp_artifact_write` directly for corpus files and never touches `.uacp/lessons/` / `.uacp/knowledge/` on the filesystem. (In-process kernel code may call `engines.oracle.write_corpus` directly; #119 exposed the tool so a tool-surface-only agent no longer has to.)

---

## Step 1 — Extract lessons to OKF

For each durable lesson in the gate artifact `resolutions/{run_id}-lessons.yaml`:

1. Assign a **kebab-case `id`** named by the lesson **topic**, not the run or date (e.g. `governed-writer-discipline`, not `phase5-lesson-1`). This makes lessons stable across reruns.
2. Build the OKF frontmatter (see `engines/domain/corpus.py Lesson` dataclass):
   - `type: lesson`
   - `id`: topic-keyed kebab-case
   - `title`, `project` (current project key), `domains`, `invariants`, `affected_paths`, `severity`
   - `source_run`: the current run_id
   - `extracted_at`: ISO timestamp of now
   - `eligible: 0`, `recurrences: 0`, `bes: 0.5` (initial prior — BES is recomputed in Step 2)
   - `promoted_to: null`
   - `tags`: optional domain tags
3. Persist the lesson by calling the **`uacp_corpus_write`** tool with `kind: lesson`, `okf:` the full OKF markdown doc, and `authority_artifact: resolutions/{run_id}-lessons.yaml`. If the file exists (same topic extracted in a prior run), it **overwrites** — the recompute in Step 2 will refresh fields (no idempotency marker needed; id is topic-stable). *(In-process kernel code may instead call `engines.oracle.write_corpus(root, kind="lesson", okf=..., run_id=..., authority_artifact=...)`.)*

---

## Step 2 — Recompute BES across all project lessons

After extracting, recompute BES for **every** lesson in `.uacp/lessons/` for this project:

```python
from engines.domain.corpus import recompute_bes
from engines.oracle import corpus_writer

# Read the corpus through the Oracle (single owner of corpus read+write).
lessons = corpus_writer.load_lessons(root)
resolved_runs = ...  # state-engine input: resolved-run manifests handed to RESOLVE
now_iso = "<RESOLVE timestamp>"

for lesson in lessons:
    updated = recompute_bes(lesson, resolved_runs, now=now_iso)
    if updated != lesson:
        corpus_writer.persist_lesson(
            root, updated, run_id=run_id,
            authority_artifact=f"resolutions/{run_id}-lessons.yaml",
        )
```

`recompute_bes` is a pure scorer in `engines.domain.corpus`; the corpus I/O (load + persist) is the Oracle's. The resolved-run manifests live at `.uacp/state/runs/<run_id>.yaml` and carry `started_at`, `domains`, and `findings` (each finding: `invariant`, `domain`); they are read by the **state engine** and supplied to RESOLVE as eligibility evidence — they are NOT Oracle inputs. Use only runs with `status: resolved`.

---

## Step 3 — Promotion check and distillation

After BES recompute, run the promotion check over the updated lessons:

```python
from engines.domain.corpus import promotion_candidate
import tomllib

with open("config/uacp.toml", "rb") as f:
    cfg = tomllib.load(f)
thresholds = cfg.get("memory", {}).get("distillation", {})

candidates = [
    (lesson, promotion_candidate(lesson, thresholds))
    for lesson in updated_lessons
    if promotion_candidate(lesson, thresholds) is not None
]
```

For each `"effective"` or `"chronic"` candidate, run the **distillation step**:

### Distillation loop

1. **Gather the cluster**: all lessons sharing the same class/domain/invariant as the candidate, plus existing `.uacp/knowledge/` docs on the same topic.
2. **Dispatch Agent Council synthesis** (see `../uacp-core/references/agent-council-followthrough.md`) to abstract a generalized pattern from the cluster.
3. **Extend-over-create**: if a knowledge doc already owns the topic (`id` matches or the council identifies an existing item), update it and append to `derived_from`; otherwise create a new `KnowledgeItem` OKF (`type: pattern` or `type: digest`).
4. Persist the knowledge doc via the **`uacp_corpus_write`** tool (`kind: knowledge`, `okf: <the OKF doc>`).
5. Set **backlinks**:
   - On the knowledge doc: `derived_from` (list of lesson ids used as input).
   - On each promoted lesson: `promoted_to = <knowledge_id>`.
   - Re-persist each modified lesson via **`uacp_corpus_write`** (`kind: lesson`).

---

## Top-down intake (non-lesson knowledge)

Design docs, ADR digests, and research analysis may author `.uacp/knowledge/` without a lesson backing them. Author a knowledge OKF doc and persist it via the **`uacp_corpus_write`** tool (`kind: knowledge`). Set `derived_from: []` and `scope: shared` or the project key as appropriate.

> **Tool-surface scope (#119).** The `uacp_corpus_write` tool covers the per-doc PERSIST of Step 1, Step 3, and top-down intake — the operations that blocked a tool-surface-only agent from doing lesson extraction. The whole-corpus **read + recompute** loops (Step 2 BES recompute; Step 3's cluster-gather) remain in-process kernel/Oracle work (`engines.oracle` owns corpus read); exposing a batch-recompute tool is a #119 follow-on if a tool-surface agent ever needs to drive it.

---

## Path resolution

RESOLVE never resolves corpus paths itself — the Oracle corpus-write surface owns
that. `engines.oracle.corpus_writer` resolves the governed corpus directories
through the config resolver (`get_config(root).resolve(root, "lessons" | "knowledge")`)
internally, both for reads (`load_lessons` / `load_knowledge`) and writes
(`persist_lesson` / `persist_knowledge`). Do not hard-code `.uacp/lessons/` or
`.uacp/knowledge/`, and do not load the corpus directories directly — route every
corpus access through `engines.oracle.corpus_writer`.
