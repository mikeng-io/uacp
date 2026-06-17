---
type: contract
title: RESOLVE lesson OKF extraction, BES recompute, and distillation
description: Operational procedure for extracting durable lessons to .uacp/lessons/, recomputing BES, and promoting lessons to .uacp/knowledge/ at RESOLVE time.
tags: [resolve, lessons, knowledge, corpus, bes, distillation]
timestamp: "2026-06-17"
---

## Purpose

After RESOLVE writes `resolutions/{run_id}-lessons.yaml` (the gate artifact), durable lessons are extracted as OKF markdown files into `.uacp/lessons/<id>.md` and scored for effectiveness. High-scoring or chronically-recurring lessons are promoted to `.uacp/knowledge/`.

All writes go through `uacp_artifact_write` (governed; `lessons/` and `knowledge/` are in scope per `config/uacp.toml [scope.tool_path_capabilities]`).

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
3. Write to `.uacp/lessons/<id>.md` via `uacp_artifact_write`. If the file exists (same topic extracted in a prior run), **overwrite** — the recompute in Step 2 will refresh fields (no idempotency marker needed; id is topic-stable).

---

## Step 2 — Recompute BES across all project lessons

After extracting, recompute BES for **every** lesson in `.uacp/lessons/` for this project:

```python
from engines.domain.corpus import load_lessons_dir, recompute_bes
from pathlib import Path

lessons = load_lessons_dir(root / ".uacp" / "lessons")
resolved_runs = ...  # load from .uacp/state/runs/*.yaml (started_at, domains, findings)
now_iso = "<RESOLVE timestamp>"

for lesson in lessons:
    updated = recompute_bes(lesson, resolved_runs, now=now_iso)
    if updated != lesson:
        # write updated OKF via uacp_artifact_write
        ...
```

The resolved-run manifests live at `.uacp/state/runs/<run_id>.yaml` and carry `started_at`, `domains`, and `findings` (each finding: `invariant`, `domain`). Load only runs with `status: resolved`.

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
4. Write the knowledge doc to `.uacp/knowledge/<id>.md` via `uacp_artifact_write`.
5. Set **backlinks**:
   - On the knowledge doc: `derived_from` (list of lesson ids used as input).
   - On each promoted lesson: `promoted_to = <knowledge_id>`.
   - Re-write each modified lesson via `uacp_artifact_write`.

---

## Top-down intake (non-lesson knowledge)

Design docs, ADR digests, and research analysis may write directly to `.uacp/knowledge/` without a lesson backing them. Use `KnowledgeItem.from_okf` / `to_okf` for serialization and `uacp_artifact_write` for the write. Set `derived_from: []` and `scope: shared` or the project key as appropriate.

---

## Path resolution

All corpus paths resolve through the config resolver:

```python
from config import get_config
from pathlib import Path

root = Path.cwd()  # or project root
cfg = get_config(root)
lessons_dir = cfg.resolve(root, "lessons")           # .uacp/lessons/
knowledge_dir = cfg.resolve(root, "knowledge")       # .uacp/knowledge/
```

Do not hard-code `.uacp/lessons/` or `.uacp/knowledge/` — always go through `get_config(root).resolve(root, <key>)`.
