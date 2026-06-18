# Lesson & Knowledge Corpus + Distillation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build UACP's two governed prior-art corpora — per-run **lessons** (`.uacp/lessons/<id>.md`) and distilled **knowledge** (`.uacp/knowledge/<id>.md`) as OKF markdown — with a BES effectiveness scorer, RESOLVE-phase lesson extraction + BES recompute, and a recurrence-gated lesson→knowledge distillation/promotion loop, migrating the legacy top-level `knowledge/` location and config onto the `.uacp/` namespace.

**Architecture:** A new `engines/domain/corpus.py` module under `skills/uacp-core/scripts/` holds pure, side-effect-free dataclasses (`Lesson`, `KnowledgeItem`), an OKF frontmatter parser/serializer, the BES formula + bonus-bucketing, and the recurrence/eligibility computation over a project's resolved-run manifests. Loaders read OKF files from the governed namespace via `config.get_config(root).resolve(root, <path_key>, ...)`; writes go through the existing `uacp_artifact_write` governed writer (`artifact.uacp` category — already covers `knowledge/`, extended to `lessons/`). Promotion thresholds are operator knobs in `config/uacp.toml [memory.distillation]`; the council-synthesis step is invoked by `uacp-resolve` skill instruction (a `references/` digest), not by the kernel.

**Tech Stack:** Python, pytest, ruff, PyYAML, OKF markdown, .uacp/ namespace, governed writers

**Depends on:** nothing to start; the Oracle engine plan (C) consumes this corpus. Related: design `2026-06-17-lesson-knowledge-corpus-design.md`. Build order: **B first** (this is the dependency root — Plan A and Plan C both reference its paths/schema/BES). Run the live migration only after FIX 1/FIX 5 are applied.

---

## Conventions for every task

- **Test runner:** from repo root `/Users/mike/Workplace/uacp`. Tests are auto-discovered under `tests/unit/`; `tests/conftest.py` already puts `skills/uacp-core/scripts/` on `sys.path`, so `from engines.domain.corpus import ...` works in tests with no extra path hacks.
- **New engine module:** `skills/uacp-core/scripts/engines/domain/corpus.py`. Pure functions + dataclasses only — **no disk writes, no `print`, never raises to caller for malformed input** (mirror `engines/io/loaders.py` "return a result, never raise" discipline where loaders are involved).
- **New test file:** `tests/unit/test_corpus.py` (single file grows task-by-task).
- **Lint/format after each impl:** `ruff check skills/uacp-core/scripts/engines/domain/corpus.py && ruff format --check skills/uacp-core/scripts/engines/domain/corpus.py`
- **Commit** after each green task. Branch first (do not write to `main`): `git checkout -b uacp/lesson-knowledge-corpus`.
- **Path resolution is authoritative:** `.uacp/lessons/<id>.md` resolves as `get_config(root).resolve(root, "lessons", f"{id}.md")` **once Task 11 adds the `lessons` field to `[paths]`**. Until then, tasks that need the path use the literal `base / "lessons"`; Task 11 makes it a declared key. Knowledge already resolves via the existing `knowledge` `[paths]` key.

---

## Task 1 — `Lesson` dataclass + OKF frontmatter parser (load)

**Failing test** — append to `tests/unit/test_corpus.py`:
```python
import textwrap
from engines.domain.corpus import Lesson, parse_okf, OKFParseError


def _lesson_md() -> str:
    return textwrap.dedent("""\
        ---
        type: lesson
        id: kanban-guard-resolve-bypass
        title: Kanban guard must not bypass resolve
        project: uacp
        domains: [kanban, runtime]
        invariants: [no-main-writes]
        affected_paths: ["state/**"]
        severity: HIGH
        source_run: phase5-kanban-guard-20260514
        extracted_at: "2026-05-14T00:00:00+00:00"
        eligible: 0
        recurrences: 0
        bes: 0.5
        promoted_to: null
        tags: [guard, resolve]
        ---
        ## description
        Doing X in run R caused failure F.

        ## prohibition
        Do not do X.
        """)


def test_parse_okf_splits_frontmatter_and_body():
    fm, body = parse_okf(_lesson_md())
    assert fm["type"] == "lesson"
    assert fm["domains"] == ["kanban", "runtime"]
    assert body.startswith("## description")


def test_parse_okf_rejects_missing_frontmatter():
    import pytest
    with pytest.raises(OKFParseError):
        parse_okf("no frontmatter here\n")


def test_lesson_from_okf_round_trip_fields():
    lesson = Lesson.from_okf(_lesson_md())
    assert lesson.id == "kanban-guard-resolve-bypass"
    assert lesson.project == "uacp"
    assert lesson.domains == ["kanban", "runtime"]
    assert lesson.invariants == ["no-main-writes"]
    assert lesson.severity == "HIGH"
    assert lesson.eligible == 0
    assert lesson.recurrences == 0
    assert lesson.bes == 0.5
    assert lesson.promoted_to is None
    assert "Do not do X." in lesson.body
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q` → `ModuleNotFoundError: engines.domain.corpus`.

**Minimal impl** — create `skills/uacp-core/scripts/engines/domain/corpus.py`:
```python
"""Lesson & knowledge corpora — OKF dataclasses, BES scorer, recurrence math.

Pure, side-effect-free. No disk writes here (governed writers handle that) and
no exceptions escape the loaders; only the explicit parse helpers raise, and
callers that load from disk catch and degrade. Mirrors engines/io/loaders.py
discipline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml


class OKFParseError(ValueError):
    """Raised when an OKF document lacks a well-formed frontmatter block."""


def parse_okf(text: str) -> tuple[dict[str, Any], str]:
    """Split an OKF markdown doc into (frontmatter dict, body str).

    Frontmatter is a leading ``---`` ... ``---`` YAML block. Raises
    OKFParseError if the opening fence or closing fence is absent.
    """
    if not text.startswith("---"):
        raise OKFParseError("OKF doc must begin with a '---' frontmatter fence")
    rest = text[len("---"):]
    end = rest.find("\n---")
    if end == -1:
        raise OKFParseError("OKF doc missing closing '---' frontmatter fence")
    fm_text = rest[:end]
    body = rest[end + len("\n---"):].lstrip("\n")
    fm = yaml.safe_load(fm_text) or {}
    if not isinstance(fm, dict):
        raise OKFParseError("OKF frontmatter must be a YAML mapping")
    return fm, body


@dataclass
class Lesson:
    id: str
    title: str
    project: str
    domains: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    affected_paths: list[str] = field(default_factory=list)
    severity: str = "MEDIUM"
    source_run: str = ""
    extracted_at: str = ""
    eligible: int = 0
    recurrences: int = 0
    bes: float = 0.5
    promoted_to: str | None = None
    tags: list[str] = field(default_factory=list)
    body: str = ""

    @classmethod
    def from_okf(cls, text: str) -> "Lesson":
        fm, body = parse_okf(text)
        return cls(
            id=str(fm["id"]),
            title=str(fm.get("title", "")),
            project=str(fm.get("project", "")),
            domains=list(fm.get("domains") or []),
            invariants=list(fm.get("invariants") or []),
            affected_paths=list(fm.get("affected_paths") or []),
            severity=str(fm.get("severity", "MEDIUM")),
            source_run=str(fm.get("source_run", "")),
            extracted_at=str(fm.get("extracted_at", "")),
            eligible=int(fm.get("eligible", 0)),
            recurrences=int(fm.get("recurrences", 0)),
            bes=float(fm.get("bes", 0.5)),
            promoted_to=(fm.get("promoted_to") or None),
            tags=list(fm.get("tags") or []),
            body=body,
        )
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q`

**Commit:** `feat(corpus): Lesson dataclass + OKF frontmatter parser`

---

## Task 2 — `Lesson.to_okf()` round-trip serializer

**Failing test** — append:
```python
def test_lesson_to_okf_round_trips():
    original = Lesson.from_okf(_lesson_md())
    serialized = original.to_okf()
    reparsed = Lesson.from_okf(serialized)
    assert reparsed == original


def test_lesson_to_okf_emits_type_lesson_first():
    serialized = Lesson.from_okf(_lesson_md()).to_okf()
    assert serialized.startswith("---\ntype: lesson\n")
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k to_okf` → `AttributeError: 'Lesson' object has no attribute 'to_okf'`.

**Minimal impl** — add to `corpus.py` `Lesson`:
```python
    def to_okf(self) -> str:
        fm = {
            "type": "lesson",
            "id": self.id,
            "title": self.title,
            "project": self.project,
            "domains": self.domains,
            "invariants": self.invariants,
            "affected_paths": self.affected_paths,
            "severity": self.severity,
            "source_run": self.source_run,
            "extracted_at": self.extracted_at,
            "eligible": self.eligible,
            "recurrences": self.recurrences,
            "bes": self.bes,
            "promoted_to": self.promoted_to,
            "tags": self.tags,
        }
        fm_text = yaml.safe_dump(fm, sort_keys=False, default_flow_style=False)
        return f"---\n{fm_text}---\n{self.body}"
```
> `sort_keys=False` preserves the design's field order; `type: lesson` is dict-first so the assertion holds.

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k to_okf`

**Commit:** `feat(corpus): Lesson.to_okf round-trip serializer`

---

## Task 3 — `KnowledgeItem` dataclass + loader/serializer

**Failing test** — append:
```python
def _knowledge_md() -> str:
    return textwrap.dedent("""\
        ---
        type: pattern
        id: governed-writer-discipline
        title: Always route protected writes through a governed writer
        description: How to satisfy the no-raw-writes invariant.
        tags: [governance, writers]
        domains: [runtime, governance]
        scope: shared
        derived_from: [kanban-guard-resolve-bypass]
        timestamp: "2026-06-17"
        ---
        Body prose explaining the pattern.
        """)


def test_knowledge_from_okf():
    from engines.domain.corpus import KnowledgeItem
    k = KnowledgeItem.from_okf(_knowledge_md())
    assert k.type == "pattern"
    assert k.id == "governed-writer-discipline"
    assert k.scope == "shared"
    assert k.derived_from == ["kanban-guard-resolve-bypass"]
    assert k.domains == ["runtime", "governance"]
    assert "Body prose" in k.body


def test_knowledge_rejects_lesson_type():
    import pytest
    from engines.domain.corpus import KnowledgeItem
    bad = _knowledge_md().replace("type: pattern", "type: lesson")
    with pytest.raises(ValueError):
        KnowledgeItem.from_okf(bad)


def test_knowledge_to_okf_round_trips():
    from engines.domain.corpus import KnowledgeItem
    original = KnowledgeItem.from_okf(_knowledge_md())
    assert KnowledgeItem.from_okf(original.to_okf()) == original
```
> Knowledge OKF `type ∈ {pattern, digest, analysis, contract}` per design — `lesson` is rejected. Design uses `project|shared`; modeled as a single `scope` field (`"shared"` or a project key).

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k knowledge`

**Minimal impl** — add to `corpus.py`:
```python
KNOWLEDGE_TYPES = ("pattern", "digest", "analysis", "contract")


@dataclass
class KnowledgeItem:
    id: str
    title: str
    type: str = "pattern"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    scope: str = "shared"  # "shared" or a project key
    derived_from: list[str] = field(default_factory=list)
    timestamp: str = ""
    body: str = ""

    @classmethod
    def from_okf(cls, text: str) -> "KnowledgeItem":
        fm, body = parse_okf(text)
        ktype = str(fm.get("type", "pattern"))
        if ktype not in KNOWLEDGE_TYPES:
            raise ValueError(
                f"knowledge type {ktype!r} must be one of {KNOWLEDGE_TYPES}"
            )
        return cls(
            id=str(fm["id"]),
            title=str(fm.get("title", "")),
            type=ktype,
            description=str(fm.get("description", "")),
            tags=list(fm.get("tags") or []),
            domains=list(fm.get("domains") or []),
            scope=str(fm.get("scope", "shared")),
            derived_from=list(fm.get("derived_from") or []),
            timestamp=str(fm.get("timestamp", "")),
            body=body,
        )

    def to_okf(self) -> str:
        fm = {
            "type": self.type,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "domains": self.domains,
            "scope": self.scope,
            "derived_from": self.derived_from,
            "timestamp": self.timestamp,
        }
        fm_text = yaml.safe_dump(fm, sort_keys=False, default_flow_style=False)
        return f"---\n{fm_text}---\n{self.body}"
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k knowledge`

**Commit:** `feat(corpus): KnowledgeItem dataclass + loader/serializer`

---

## Task 4 — BES scorer: the `eligible == 0` prior + smoothed posterior

**Failing test** — append (covers the `eligible==0` prior and the Beta(1,1) smoothing exactly as the design formula):
```python
from engines.domain.corpus import bes_score


def test_bes_prior_when_no_eligible_runs():
    # eligible == 0 -> prior 0.5, regardless of days
    assert bes_score(eligible=0, recurrences=0, days_since_extracted=0) == 0.5
    assert bes_score(eligible=0, recurrences=0, days_since_extracted=1000) == 0.5


def test_bes_smoothed_posterior_no_recurrence():
    # eligible=8, recurrences=0, days=0 (recency=1.0)
    # successes=8 ; smoothed=(8+1)/(8+2)=0.9 ; bes=0.9*1.0
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=0) == 0.9


def test_bes_smoothed_posterior_with_recurrences():
    # eligible=8, recurrences=4, days=0
    # successes=4 ; smoothed=(4+1)/(8+2)=0.5 ; bes=0.5
    assert bes_score(eligible=8, recurrences=4, days_since_extracted=0) == 0.5


def test_bes_all_recurrences_floor_not_zero():
    # eligible=3, recurrences=3 -> successes=0 ; smoothed=(0+1)/(3+2)=0.2
    assert bes_score(eligible=3, recurrences=3, days_since_extracted=0) == 0.2
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k bes` → `ImportError: cannot import name 'bes_score'`.

**Minimal impl** — add to `corpus.py`:
```python
def bes_score(*, eligible: int, recurrences: int, days_since_extracted: float) -> float:
    """Bayesian effectiveness score (ported from Trustless ACP).

        if eligible == 0:  BES = 0.5                      # prior (no data)
        successes = eligible - recurrences
        smoothed  = (successes + 1) / (eligible + 2)      # Beta(1,1) posterior mean
        recency   = max(0.5, 1 - 0.5 * days/365)
        BES       = smoothed * recency
    """
    if eligible == 0:
        return 0.5
    successes = eligible - recurrences
    smoothed = (successes + 1) / (eligible + 2)
    recency = max(0.5, 1 - 0.5 * (days_since_extracted / 365))
    return smoothed * recency
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k bes`

**Commit:** `feat(corpus): BES scorer with eligible==0 prior + Beta(1,1) smoothing`

---

## Task 5 — BES recency floor

**Failing test** — append:
```python
def test_bes_recency_floor_at_half():
    # eligible=8, recurrences=0, smoothed=0.9.
    # days=365 -> recency = max(0.5, 1-0.5) = 0.5 -> bes=0.45
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=365) == 0.45
    # days far past 2*365 must NOT drop below floor: recency clamps to 0.5 -> 0.45
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=100000) == 0.45


def test_bes_recency_partial_decay():
    # days=182.5 -> recency = 1-0.5*(0.5) = 0.75 ; smoothed=0.9 -> 0.675
    assert bes_score(eligible=8, recurrences=0, days_since_extracted=182.5) == 0.675
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k recency` — the floor test for `days=100000` fails only if the impl forgot `max(0.5, ...)`. (If Task 4's impl already has the floor, this task is a *characterization lock* — keep it: it pins the floor branch explicitly.)

**Minimal impl:** already satisfied by Task 4's `max(0.5, ...)`. If the floor test fails, the fix is to wrap recency in `max(0.5, ...)`. No new code expected; this task exists to lock the floor branch with assertions.

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k recency`

**Commit:** `test(corpus): lock BES recency floor branch`

---

## Task 6 — BES → ranking bonus bucketing (all tiers)

Design rule: `≥.85→5, ≥.70→4, ≥.55→3, ≥.40→2, else→1; +1 if CRITICAL/HIGH; −2 if BES<.4 & eligible≥5`.

**Failing test** — append (one assertion per tier + each modifier):
```python
from engines.domain.corpus import bes_bonus


def test_bes_bonus_base_tiers():
    assert bes_bonus(bes=0.90, severity="LOW", eligible=10) == 5
    assert bes_bonus(bes=0.85, severity="LOW", eligible=10) == 5   # boundary inclusive
    assert bes_bonus(bes=0.70, severity="LOW", eligible=10) == 4   # boundary inclusive
    assert bes_bonus(bes=0.69, severity="LOW", eligible=10) == 3
    assert bes_bonus(bes=0.55, severity="LOW", eligible=10) == 3   # boundary inclusive
    assert bes_bonus(bes=0.40, severity="LOW", eligible=10) == 2   # boundary inclusive
    assert bes_bonus(bes=0.39, severity="LOW", eligible=3) == 1    # eligible<5 so no -2


def test_bes_bonus_severity_modifier():
    # +1 for CRITICAL/HIGH, applied on top of the tier
    assert bes_bonus(bes=0.90, severity="CRITICAL", eligible=10) == 6
    assert bes_bonus(bes=0.55, severity="HIGH", eligible=10) == 4
    assert bes_bonus(bes=0.55, severity="MEDIUM", eligible=10) == 3


def test_bes_bonus_chronic_penalty():
    # BES<.4 AND eligible>=5 -> -2, stacking with the base tier of 1
    assert bes_bonus(bes=0.30, severity="LOW", eligible=8) == -1
    # penalty does not apply below the eligibility floor
    assert bes_bonus(bes=0.30, severity="LOW", eligible=4) == 1
    # a CRITICAL chronic lesson: tier 1 +1 (sev) -2 (chronic) = 0
    assert bes_bonus(bes=0.30, severity="CRITICAL", eligible=8) == 0
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k bonus`

**Minimal impl** — add to `corpus.py`:
```python
def bes_bonus(*, bes: float, severity: str, eligible: int) -> int:
    """Map a BES + lesson context to a retrieval ranking bonus.

    Tiers: >=.85->5, >=.70->4, >=.55->3, >=.40->2, else 1.
    +1 if severity in {CRITICAL, HIGH}; -2 if bes<.4 AND eligible>=5.
    """
    if bes >= 0.85:
        bonus = 5
    elif bes >= 0.70:
        bonus = 4
    elif bes >= 0.55:
        bonus = 3
    elif bes >= 0.40:
        bonus = 2
    else:
        bonus = 1
    if severity in ("CRITICAL", "HIGH"):
        bonus += 1
    if bes < 0.40 and eligible >= 5:
        bonus -= 2
    return bonus
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k bonus`

**Commit:** `feat(corpus): BES->ranking bonus bucketing (5 tiers + modifiers)`

---

## Task 7 — eligibility & recurrence over resolved runs (the BES inputs)

Design: *eligible* = later resolved runs sharing ≥1 domain, started after the lesson; *recurrence* = a later eligible run with a finding matching the **same invariant AND domain**. This task computes `(eligible, recurrences)` for one lesson from a list of plain resolved-run records (dicts) — no disk yet.

**Failing test** — append:
```python
from engines.domain.corpus import count_eligibility


def _run(run_id, started_at, domains, findings=None):
    # findings: list of (invariant, domain)
    return {
        "run_id": run_id,
        "started_at": started_at,
        "domains": domains,
        "findings": [{"invariant": i, "domain": d} for (i, d) in (findings or [])],
    }


def test_eligibility_counts_later_overlapping_runs():
    lesson = Lesson.from_okf(_lesson_md())  # domains=[kanban,runtime], invariants=[no-main-writes], extracted 2026-05-14
    runs = [
        _run("before", "2026-05-01T00:00:00+00:00", ["kanban"]),          # earlier -> not eligible
        _run("no-overlap", "2026-06-01T00:00:00+00:00", ["docs"]),        # later, no domain overlap -> not eligible
        _run("eligible-clean", "2026-06-01T00:00:00+00:00", ["kanban"]),  # later + overlap -> eligible, no recurrence
        _run("eligible-recur", "2026-06-02T00:00:00+00:00", ["runtime"],
             findings=[("no-main-writes", "runtime")]),                   # eligible + recurrence
    ]
    eligible, recurrences = count_eligibility(lesson, runs)
    assert eligible == 2
    assert recurrences == 1


def test_recurrence_requires_both_invariant_and_domain():
    lesson = Lesson.from_okf(_lesson_md())
    runs = [
        # right invariant, wrong domain -> NOT a recurrence (but still eligible via domain overlap)
        _run("r1", "2026-06-01T00:00:00+00:00", ["kanban"],
             findings=[("no-main-writes", "docs")]),
        # right domain, wrong invariant -> NOT a recurrence
        _run("r2", "2026-06-01T00:00:00+00:00", ["runtime"],
             findings=[("some-other", "runtime")]),
    ]
    eligible, recurrences = count_eligibility(lesson, runs)
    assert eligible == 2
    assert recurrences == 0
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k eligibility`

**Minimal impl** — add to `corpus.py`:
```python
from datetime import datetime


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def count_eligibility(lesson: Lesson, resolved_runs: list[dict]) -> tuple[int, int]:
    """Return (eligible, recurrences) for ``lesson`` over ``resolved_runs``.

    eligible   = later runs (started_at > lesson.extracted_at) sharing >=1 domain.
    recurrence = an eligible run carrying a finding whose (invariant, domain)
                 both match the lesson's invariants and domains.
    Robust to malformed records: unparseable timestamps drop the run.
    """
    lesson_ts = _parse_ts(lesson.extracted_at)
    lesson_domains = set(lesson.domains)
    lesson_invariants = set(lesson.invariants)
    eligible = 0
    recurrences = 0
    for run in resolved_runs:
        started = _parse_ts(run.get("started_at", ""))
        if lesson_ts is None or started is None or started <= lesson_ts:
            continue
        run_domains = set(run.get("domains") or [])
        if not (run_domains & lesson_domains):
            continue
        eligible += 1
        for finding in run.get("findings") or []:
            inv = finding.get("invariant")
            dom = finding.get("domain")
            if inv in lesson_invariants and dom in lesson_domains:
                recurrences += 1
                break  # one recurrence per run
    return eligible, recurrences
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k eligibility`

**Commit:** `feat(corpus): eligibility + recurrence counting over resolved runs`

---

## Task 8 — `recompute_bes` updates a Lesson's eligible/recurrences/bes

**Failing test** — append:
```python
from engines.domain.corpus import recompute_bes


def test_recompute_bes_updates_lesson_fields():
    lesson = Lesson.from_okf(_lesson_md())
    runs = [
        _run("e1", "2026-06-01T00:00:00+00:00", ["kanban"]),
        _run("e2", "2026-06-02T00:00:00+00:00", ["runtime"]),
    ]
    updated = recompute_bes(lesson, runs, now="2026-05-14T00:00:00+00:00")
    assert updated.eligible == 2
    assert updated.recurrences == 0
    # eligible=2,rec=0,days=0 -> smoothed=(2+1)/(2+2)=0.75 ; recency=1 ; bes=0.75
    assert updated.bes == 0.75
    # original is not mutated (pure)
    assert lesson.eligible == 0
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k recompute`

**Minimal impl** — add to `corpus.py`:
```python
import dataclasses


def recompute_bes(lesson: Lesson, resolved_runs: list[dict], *, now: str) -> Lesson:
    """Return a new Lesson with eligible/recurrences/bes recomputed.

    ``now`` is an ISO timestamp (RESOLVE-time). Pure — input lesson untouched.
    """
    eligible, recurrences = count_eligibility(lesson, resolved_runs)
    extracted = _parse_ts(lesson.extracted_at)
    now_ts = _parse_ts(now)
    if extracted is not None and now_ts is not None:
        days = max(0.0, (now_ts - extracted).total_seconds() / 86400)
    else:
        days = 0.0
    bes = bes_score(eligible=eligible, recurrences=recurrences, days_since_extracted=days)
    updated = dataclasses.replace(lesson, eligible=eligible, recurrences=recurrences, bes=round(bes, 6))
    return updated
```
> `dataclasses.replace` is version-proof (available since Python 3.7) and cleaner than the `copy.replace` + `hasattr` probe that was needed for 3.13+ only. Round to 6 dp to avoid float noise drifting frontmatter on every recompute.

Adjust the Task 8 assertion if rounding changes `0.75` — it does not (`0.75` is exact).

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k recompute`

**Commit:** `feat(corpus): recompute_bes recomputes lesson effectiveness fields`

---

## Task 9 — corpus disk loaders (read `.uacp/lessons/`, `.uacp/knowledge/`)

Read-models loaded from the governed namespace, **never raising** — mirror `engines/io/loaders.py`. Knowledge resolves via the existing `knowledge` `[paths]` key; lessons resolve under `base / "lessons"` until Task 11 promotes it to a declared key. These loaders take an explicit directory `Path` so they are decoupled from config (the config wiring is exercised in Task 11's path test).

**Failing test** — append:
```python
from engines.domain.corpus import load_lessons_dir, load_knowledge_dir


def test_load_lessons_dir(tmp_path):
    d = tmp_path / "lessons"
    d.mkdir()
    (d / "kanban-guard-resolve-bypass.md").write_text(_lesson_md(), encoding="utf-8")
    (d / "not-a-lesson.txt").write_text("ignored", encoding="utf-8")
    lessons = load_lessons_dir(d)
    assert len(lessons) == 1
    assert lessons[0].id == "kanban-guard-resolve-bypass"


def test_load_lessons_dir_skips_malformed(tmp_path):
    d = tmp_path / "lessons"
    d.mkdir()
    (d / "good.md").write_text(_lesson_md(), encoding="utf-8")
    (d / "bad.md").write_text("no frontmatter\n", encoding="utf-8")
    lessons = load_lessons_dir(d)  # must NOT raise
    assert [l.id for l in lessons] == ["kanban-guard-resolve-bypass"]


def test_load_lessons_dir_missing_is_empty(tmp_path):
    assert load_lessons_dir(tmp_path / "nonexistent") == []


def test_load_knowledge_dir(tmp_path):
    d = tmp_path / "knowledge"
    d.mkdir()
    (d / "governed-writer-discipline.md").write_text(_knowledge_md(), encoding="utf-8")
    (d / "indexes").mkdir()  # subdir must be ignored, not crash
    items = load_knowledge_dir(d)
    assert len(items) == 1
    assert items[0].id == "governed-writer-discipline"
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k "load_lessons or load_knowledge"`

**Minimal impl** — add to `corpus.py`:
```python
from pathlib import Path


def load_lessons_dir(directory: Path) -> list[Lesson]:
    """Load every ``*.md`` lesson in ``directory``; skip malformed; never raise."""
    out: list[Lesson] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.md")):
        try:
            out.append(Lesson.from_okf(path.read_text(encoding="utf-8")))
        except (OKFParseError, KeyError, ValueError, OSError):
            continue
    return out


def load_knowledge_dir(directory: Path) -> list[KnowledgeItem]:
    """Load every ``*.md`` knowledge item in ``directory``; skip malformed; never raise.

    Subdirectories (e.g. ``indexes/``) are ignored by the ``*.md`` glob.
    """
    out: list[KnowledgeItem] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.md")):
        try:
            out.append(KnowledgeItem.from_okf(path.read_text(encoding="utf-8")))
        except (OKFParseError, KeyError, ValueError, OSError):
            continue
    return out
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k "load_lessons or load_knowledge"`

**Commit:** `feat(corpus): non-raising disk loaders for lessons + knowledge dirs`

---

## Task 10 — promotion-candidate detector (recurrence-gated thresholds)

Design trigger: **consistently effective** (`bes ≥ threshold AND eligible ≥ N` → positive pattern) OR **chronically recurring** (recurs across `≥ K` distinct runs/domains → strong prohibition). Thresholds are operator knobs (added to config in this task) with code defaults.

**Failing test** — append:
```python
from engines.domain.corpus import promotion_candidate, PROMOTION_DEFAULTS


def _scored_lesson(bes, eligible, recurrences):
    lesson = Lesson.from_okf(_lesson_md())
    lesson.bes = bes
    lesson.eligible = eligible
    lesson.recurrences = recurrences
    return lesson


def test_promotion_consistently_effective():
    # bes>=.85 and eligible>=5 with defaults -> "effective" candidate
    cand = promotion_candidate(_scored_lesson(0.90, 6, 0), PROMOTION_DEFAULTS)
    assert cand == "effective"


def test_promotion_chronically_recurring():
    # recurrences >= K (default 3) -> "chronic" candidate
    cand = promotion_candidate(_scored_lesson(0.30, 8, 3), PROMOTION_DEFAULTS)
    assert cand == "chronic"


def test_promotion_none_when_below_thresholds():
    assert promotion_candidate(_scored_lesson(0.60, 2, 1), PROMOTION_DEFAULTS) is None


def test_already_promoted_is_not_a_candidate():
    lesson = _scored_lesson(0.90, 6, 0)
    lesson.promoted_to = "governed-writer-discipline"
    assert promotion_candidate(lesson, PROMOTION_DEFAULTS) is None
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k promotion`

**Minimal impl** — add to `corpus.py`:
```python
PROMOTION_DEFAULTS = {
    "effective_bes_min": 0.85,   # "consistently effective" BES cutoff
    "effective_eligible_min": 5,  # N: eligible runs required
    "chronic_recurrence_min": 3,  # K: distinct recurrences required
}


def promotion_candidate(lesson: Lesson, thresholds: dict) -> str | None:
    """Classify a (BES-recomputed) lesson as a promotion candidate.

    Returns "effective", "chronic", or None. Already-promoted lessons
    (``promoted_to`` set) are never candidates.
    """
    if lesson.promoted_to:
        return None
    t = {**PROMOTION_DEFAULTS, **(thresholds or {})}
    if lesson.bes >= t["effective_bes_min"] and lesson.eligible >= t["effective_eligible_min"]:
        return "effective"
    if lesson.recurrences >= t["chronic_recurrence_min"]:
        return "chronic"
    return None
```

Then add the operator knobs to `config/uacp.toml` under `[memory]` (use `uacp_config_write` if available; this is a plan-time config edit so a direct edit during execution is acceptable per the migration task's pattern). Insert after the `[memory.local_knowledge_locations]` block (which Task 11 repoints):
```toml
# --- Distillation / promotion thresholds (lesson -> knowledge) ----------------
# Recurrence-gated promotion knobs consumed by engines/domain/corpus.py
# (promotion_candidate). Code defaults in PROMOTION_DEFAULTS mirror these; the
# kernel falls back to those when this table is absent (fail-open: no promotion
# is non-destructive). Start conservative — design B "Open items".
[memory.distillation]
effective_bes_min = 0.85       # "consistently effective": BES cutoff
effective_eligible_min = 5     # N: eligible later runs required
chronic_recurrence_min = 3     # K: distinct recurrences -> "keeps biting us"
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k promotion`

**Commit:** `feat(corpus): recurrence-gated promotion-candidate detector + config knobs`

---

## Task 11 — add `lessons` to `[paths]` + config-resolved corpus paths

Make `.uacp/lessons/<id>.md` and `.uacp/knowledge/<id>.md` resolvable through the canonical resolver. (The index location under `.uacp/knowledge/indexes/` is owned by Plan C's raw `[oracle] index_path` config string — not a governed `[paths]` segment. Do not add an `indexes` path key here: `resolve()` hard-raises on unknown keys and nested paths are not cleanly supported.)

**Failing test** — append (uses the config resolver directly, the same way `dir_for`/`resolve` are used elsewhere):
```python
import config


def test_lessons_path_resolves_under_uacp(tmp_path):
    cfg = config.get_config(tmp_path)
    p = cfg.resolve(tmp_path, "lessons", "my-lesson.md")
    assert p == (tmp_path / ".uacp" / "lessons" / "my-lesson.md")


def test_knowledge_path_resolves_under_uacp(tmp_path):
    cfg = config.get_config(tmp_path)
    p = cfg.resolve(tmp_path, "knowledge", "my-item.md")
    assert p == (tmp_path / ".uacp" / "knowledge" / "my-item.md")
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k path` → `ValueError: unknown paths key 'lessons'`.

**Minimal impl** — two edits:

1. `skills/uacp-core/scripts/config.py`, `Paths` class — add field after `knowledge`:
```python
    knowledge: str = "knowledge"
    lessons: str = "lessons"
    config: str = "config.toml"
```

2. `config/uacp.toml`, `[paths]` block — add after `knowledge = "knowledge"`:
```toml
knowledge = "knowledge"
lessons = "lessons"
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k path`
Also run the existing config/path suite to confirm no regression: `python3 -m pytest tests/unit/ -q -k "config or path or resolve"`

**Commit:** `feat(config): add lessons path key; resolve corpora under .uacp/`

---

## Task 12 — governed-writer surface for lessons (`artifact.uacp` covers `lessons/`)

The `uacp_artifact_write` writer governs `plans/ proposals/ executions/ verification/ resolutions/ knowledge/` (see `config/uacp.toml [scope.tool_path_capabilities].uacp_artifact_write`). Lessons are a new tracked corpus under `.uacp/lessons/`; extend the writer's capability list so `uacp-resolve` can write lesson OKF files through it (not raw FS).

**Failing test** — append in a new `tests/unit/test_corpus_write_surface.py`:
```python
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_artifact_writer_can_reach_lessons_prefix():
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    caps = cfg["scope"]["tool_path_capabilities"]["uacp_artifact_write"]
    assert "lessons/" in caps
    assert "knowledge/" in caps  # unchanged


def test_artifact_category_description_mentions_lessons():
    cfg = tomllib.loads((ROOT / "config" / "uacp.toml").read_text())
    desc = cfg["guardian"]["protected_categories"]["artifact.uacp"]["description"]
    assert "lessons/" in desc
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus_write_surface.py -q`

**Minimal impl** — two edits in `config/uacp.toml`:

1. `[scope.tool_path_capabilities]`:
```toml
uacp_artifact_write = ["plans/", "proposals/", "executions/", "verification/", "resolutions/", "knowledge/", "lessons/"]
```

2. `[guardian.protected_categories."artifact.uacp"]` `description` — append `lessons/` to the enumerated dir list (e.g. `... verification/, resolutions/, knowledge/, lessons/.`).

> No code change: `uacp_artifact_write`'s handler is data-driven from these tables. Confirm by running the guardian/scope suite: `python3 -m pytest tests/unit/ -q -k "guardian or scope or artifact"`.

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus_write_surface.py -q`

**Commit:** `feat(config): extend uacp_artifact_write to govern .uacp/lessons/`

---

## Task 13 — RESOLVE extraction + distillation wiring (skill instruction + reference digest)

RESOLVE already requires `resolutions/{run_id}-lessons.yaml` (validated by `core.py:_validate_lessons_artifact`). That YAML stays as the **gate artifact**; this task adds the **OKF corpus write-through + BES recompute + promotion check** as RESOLVE skill instruction, citing a new operational digest (no `docs/` back-pointer per `uacp-skills` self-containment rule).

This is **documentation/instruction**, not kernel code — no pytest. Steps:

1. Create `skills/uacp-resolve/references/lesson-corpus-extraction.md` (OKF `type: contract`, in the index later). Content — the RESOLVE corpus procedure:
   - After the gate `resolutions/{run_id}-lessons.yaml` exists, **extract each durable lesson** into an OKF file at `.uacp/lessons/<id>.md` using the Task 1–2 frontmatter schema; write via `uacp_artifact_write` (governed; `lessons/` now in scope per Task 12). `id` is kebab-case named by the lesson *topic*, not the run/date (mirrors the OKF naming rule in `uacp-skills`). Set `project` from the current project key, `source_run` = run_id, `extracted_at` = now.
   - **Recompute BES** for the project's lessons over the resolved-run manifests (`.uacp/state/runs/*.yaml` — the producer of `started_at`/`domains`; the recompute uses `engines.domain.corpus.recompute_bes`). Re-write each changed lesson OKF via the governed writer.
   - **Run the promotion check** (`promotion_candidate`, thresholds from `config/uacp.toml [memory.distillation]`). For each `effective`/`chronic` candidate, hand off to the distillation step.
2. Append a **"Lesson corpus + distillation"** section to `skills/uacp-resolve/SKILL.md` (keep < 500 lines) that:
   - Replaces the stale `## Rules` bullet "Use `knowledge/` for durable run learning" with "Write lessons to `.uacp/lessons/<id>.md` and distilled knowledge to `.uacp/knowledge/<id>.md` via `uacp_artifact_write`."
   - Cites `references/lesson-corpus-extraction.md` with a "Read when extracting lessons at RESOLVE" pointer.
   - Documents the **distillation mechanism** (design B §"distillation loop"): gather the cluster of related lessons (same class/domain/invariant) + existing knowledge docs on the topic + design rationale; dispatch an **Agent Council synthesis** (per `../uacp-core/references/agent-council-followthrough.md`) to abstract a generalized pattern; **extend-over-create** — if a knowledge doc owns the topic, update it; else create one; write via `uacp_artifact_write` to `.uacp/knowledge/`; set `derived_from` (knowledge→lessons) and `promoted_to` (lesson→knowledge) backlinks.
   - Notes **top-down intake**: design (ADR digests) and research/analysis may author `.uacp/knowledge/` directly with no lesson behind them.

**Verification (no unit test — this is instruction):** run the skills lint, which enforces self-containment + reference-index membership:
`python3 -m pytest tests/unit/skills/ -q`
Add `references/lesson-corpus-extraction.md` to `skills/uacp-core/references/index.md` only if the lint requires shared-index membership; if the digest lives under the skill's own `references/`, the per-skill self-containment lint suffices. Resolve whatever the lint flags.

**Commit:** `docs(resolve): wire lesson OKF extraction + BES recompute + distillation`

---

## Task 14 — migrate legacy `knowledge/` + repoint config

One-time move of the tracked top-level `knowledge/lessons/*`, root-level `knowledge/*-lessons*.md` files, and other `knowledge/*.md` onto `.uacp/`, plus repointing `[memory.local_knowledge_locations]`. Follow the existing `scripts/migrate_to_uacp_dir.py` idempotent pattern.

**Classification rule (FIX 1):** The repo has two pre-OKF lesson files at the `knowledge/` ROOT (not in `knowledge/lessons/`): `phase5-kanban-guard-resolve-lessons-20260514.md` and `phase6-agent-council-operationalization-lessons-20260515.md`. These must go to `.uacp/lessons/`, not `.uacp/knowledge/` (the knowledge loader would reject or drop them). The migration classifies by **filename pattern** (`*-lessons*.md` at the root) rather than purely by directory: root-level files matching `*-lessons*.md` → `.uacp/lessons/`; all other root-level `.md` files → `.uacp/knowledge/`. If future root-level files are ambiguous, add them to a manual-triage list rather than silently misrouting them.

**FIX 5 — scenarios/gate-templates consistency:** The migration does NOT move `knowledge/scenarios/` or `knowledge/gate-templates/` into `.uacp/knowledge/`. These subdirectories remain at `knowledge/scenarios/` and `knowledge/gate-templates/` so that the `[memory.local_knowledge_locations]` entries (`scenarios = "knowledge/scenarios/"`, `gate_templates = "knowledge/gate-templates/"`) remain valid and non-dangling. Rerouting those paths is out of scope for this corpus plan.

**Failing test** — new `tests/unit/test_migrate_knowledge_corpus.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import migrate_knowledge_corpus as mig  # noqa: E402


def _legacy(tmp_path):
    (tmp_path / "knowledge" / "lessons").mkdir(parents=True)
    (tmp_path / "knowledge" / "lessons" / "old.yaml").write_text("kind: uacp.lesson\n")
    (tmp_path / "knowledge" / "topic.md").write_text("# legacy knowledge\n")
    # Two pre-OKF root-level lesson files (real repo pattern — FIX 1)
    (tmp_path / "knowledge" / "phase5-kanban-guard-resolve-lessons-20260514.md").write_text(
        "# phase 5 lessons\n"
    )
    (tmp_path / "knowledge" / "phase6-agent-council-operationalization-lessons-20260515.md").write_text(
        "# phase 6 lessons\n"
    )
    # Preserved subdirectories — NOT moved (FIX 5)
    (tmp_path / "knowledge" / "scenarios").mkdir()
    (tmp_path / "knowledge" / "gate-templates").mkdir()


def test_moves_lessons_and_knowledge_under_uacp(tmp_path):
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "lessons" / "old.yaml").exists()
    assert (tmp_path / ".uacp" / "knowledge" / "topic.md").exists()


def test_root_level_lesson_files_land_in_lessons_not_knowledge(tmp_path):
    """FIX 1: root-level *-lessons*.md files must go to .uacp/lessons/, not .uacp/knowledge/."""
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "lessons" / "phase5-kanban-guard-resolve-lessons-20260514.md").exists()
    assert (tmp_path / ".uacp" / "lessons" / "phase6-agent-council-operationalization-lessons-20260515.md").exists()
    # Must NOT appear in knowledge/
    assert not (tmp_path / ".uacp" / "knowledge" / "phase5-kanban-guard-resolve-lessons-20260514.md").exists()
    assert not (tmp_path / ".uacp" / "knowledge" / "phase6-agent-council-operationalization-lessons-20260515.md").exists()


def test_scenarios_and_gate_templates_not_moved(tmp_path):
    """FIX 5: scenarios/ and gate-templates/ stay at knowledge/ (config still points there)."""
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / "knowledge" / "scenarios").exists()
    assert (tmp_path / "knowledge" / "gate-templates").exists()
    assert not (tmp_path / ".uacp" / "knowledge" / "scenarios").exists()


def test_idempotent(tmp_path):
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    mig.migrate(tmp_path)  # must not raise
    assert (tmp_path / ".uacp" / "lessons" / "old.yaml").exists()


def test_creates_indexes_dir(tmp_path):
    _legacy(tmp_path)
    mig.migrate(tmp_path)
    assert (tmp_path / ".uacp" / "knowledge" / "indexes").is_dir()
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_migrate_knowledge_corpus.py -q`

**Minimal impl** — create `scripts/migrate_knowledge_corpus.py`:
```python
"""One-time migration: legacy top-level knowledge/ -> .uacp/ corpora (idempotent).

Classification rules:
  knowledge/lessons/*          -> .uacp/lessons/   (pre-OKF YAML lessons)
  knowledge/*-lessons*.md      -> .uacp/lessons/   (root-level lesson prose — FIX 1)
  knowledge/*.md (other)       -> .uacp/knowledge/ (knowledge items)
  knowledge/scenarios/         -> NOT moved (config still points here — FIX 5)
  knowledge/gate-templates/    -> NOT moved (config still points here — FIX 5)
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Subdirectories at knowledge/ root that are NOT part of this migration.
# Their [memory.local_knowledge_locations] entries remain unchanged.
_SKIP_SUBDIRS = {"lessons", "scenarios", "gate-templates"}


def _is_lesson_file(path: Path) -> bool:
    """True if a root-level file should be classified as a lesson (FIX 1)."""
    return "-lessons" in path.name


def migrate(root: Path) -> None:
    root = Path(root)
    base = root / ".uacp"
    legacy = root / "knowledge"
    if not legacy.exists():
        return
    lessons_dst = base / "lessons"
    knowledge_dst = base / "knowledge"
    lessons_dst.mkdir(parents=True, exist_ok=True)
    knowledge_dst.mkdir(parents=True, exist_ok=True)
    (knowledge_dst / "indexes").mkdir(exist_ok=True)

    # Move knowledge/lessons/* -> .uacp/lessons/
    legacy_lessons = legacy / "lessons"
    if legacy_lessons.is_dir():
        for item in legacy_lessons.iterdir():
            dst = lessons_dst / item.name
            if not dst.exists():
                shutil.move(str(item), str(dst))

    # Move root-level files, classifying by name (FIX 1)
    for item in legacy.iterdir():
        if item.is_dir():
            # Skip all subdirs including scenarios/ and gate-templates/ (FIX 5)
            continue
        if item.name.startswith("."):
            continue
        if _is_lesson_file(item):
            dst = lessons_dst / item.name
        else:
            dst = knowledge_dst / item.name
        if not dst.exists():
            shutil.move(str(item), str(dst))

    # Remove lessons/ subdir if now empty (idempotent: missing is fine)
    if legacy_lessons.is_dir() and not any(legacy_lessons.iterdir()):
        legacy_lessons.rmdir()
    # Do NOT rmtree legacy/ — scenarios/ and gate-templates/ still live there (FIX 5)
```

Then repoint `config/uacp.toml [memory.local_knowledge_locations]` (the legacy paths under `knowledge/`):
```toml
[memory.local_knowledge_locations]
scenarios = "knowledge/scenarios/"       # NOT moved — config path unchanged (FIX 5)
gate_templates = "knowledge/gate-templates/"  # NOT moved — config path unchanged (FIX 5)
lessons = "lessons/"                     # -> .uacp/lessons/ (canonical key: [paths].lessons)
# NOTE: the canonical authority for the lessons path is [paths].lessons above.
#       Confirm the memory reader prepends ".uacp/" to these values
#       (i.e. "lessons/" -> .uacp/lessons/, not repo-root/lessons/).
indexes = "knowledge/indexes/"           # index home owned by Plan C [oracle] index_path; not a [paths] key
```

**Run the actual migration once against the repo** during execution (after tests pass):
`python3 scripts/migrate_knowledge_corpus.py` — add an `if __name__ == "__main__": migrate(Path.cwd())` guard.

Post-migration verification steps:
1. `git status` — confirm `knowledge/phase5-kanban-guard-resolve-lessons-20260514.md`, `knowledge/phase6-agent-council-operationalization-lessons-20260515.md`, and `knowledge/lessons/*.yaml` are staged as deletes, and `.uacp/lessons/` + `.uacp/knowledge/` appear as new tracked files (not untracked, since neither path is in `.gitignore`).
2. Confirm `knowledge/scenarios/` and `knowledge/gate-templates/` are still present and unmodified.
3. Confirm the top-level `knowledge/` dir still exists (it is not removed, since scenarios/ and gate-templates/ remain).

> `.gitignore` does NOT list `.uacp/lessons/` or `.uacp/knowledge/` — those paths are tracked by *absence* of a rule (only the per-phase run dirs are explicitly ignored: `.uacp/state/`, `.uacp/proposals/`, `.uacp/plans/`, etc.). The moved corpus will therefore be committed automatically. Add only `.uacp/knowledge/indexes/` to `.gitignore` (rebuildable derived index — design table). Append under the existing `.uacp/` block:
> ```
> .uacp/knowledge/indexes/
> ```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_migrate_knowledge_corpus.py -q`

**Commit:** `feat(migrate): move legacy knowledge/ -> .uacp/lessons + .uacp/knowledge; repoint config`

---

## Task 15 — multi-project `project` scoping helpers + full-suite gate

The `project` tag already lives on every `Lesson` (Task 1) and `scope` on every `KnowledgeItem` (Task 3). Add filter helpers the Oracle (Doc C) and RESOLVE recompute use: lessons are project-local; knowledge is `this project` + `shared`.

**Failing test** — append to `tests/unit/test_corpus.py`:
```python
from engines.domain.corpus import lessons_for_project, knowledge_for_project


def test_lessons_filtered_to_project():
    a = Lesson.from_okf(_lesson_md())               # project=uacp
    b = Lesson.from_okf(_lesson_md().replace("project: uacp", "project: other"))
    b.id = "other-lesson"
    assert [l.id for l in lessons_for_project([a, b], "uacp")] == [a.id]


def test_knowledge_includes_shared_plus_project():
    from engines.domain.corpus import KnowledgeItem
    shared = KnowledgeItem.from_okf(_knowledge_md())                       # scope=shared
    local = KnowledgeItem.from_okf(_knowledge_md().replace("scope: shared", "scope: uacp"))
    local.id = "uacp-local"
    other = KnowledgeItem.from_okf(_knowledge_md().replace("scope: shared", "scope: other"))
    other.id = "other-local"
    got = {k.id for k in knowledge_for_project([shared, local, other], "uacp")}
    assert got == {shared.id, "uacp-local"}
```

**Run / expect FAIL:** `python3 -m pytest tests/unit/test_corpus.py -q -k "project"`

**Minimal impl** — add to `corpus.py`:
```python
def lessons_for_project(lessons: list[Lesson], project: str) -> list[Lesson]:
    """Lessons are project-local: keep only those tagged with ``project``."""
    return [l for l in lessons if l.project == project]


def knowledge_for_project(items: list[KnowledgeItem], project: str) -> list[KnowledgeItem]:
    """Knowledge query surface: this project's items plus shared items."""
    return [k for k in items if k.scope == project or k.scope == "shared"]
```

**Run / expect PASS:** `python3 -m pytest tests/unit/test_corpus.py -q -k project`

**Final full-suite gate:**
```bash
ruff check skills/uacp-core/scripts/engines/domain/corpus.py
ruff format --check skills/uacp-core/scripts/engines/domain/corpus.py
python3 -m pytest tests/unit/ -q
```
All green before finishing.

**Commit:** `feat(corpus): project-scoped lesson/knowledge filters`

---

## Out of scope (YAGNI — do NOT build)

- **Cross-project SHARED knowledge store location** — design B "Open items": a `shared` tier across projects needs a home (e.g. a user-level UACP knowledge dir). This plan only *marks* knowledge `scope: shared`; it does not build the cross-project store or sync. Defer until multi-project is exercised.
- **The Oracle retrieval engine (Doc C)** — `relevance` gating/ranking, embeddings, and `.uacp/knowledge/indexes/` index *building*. This plan produces the corpus and the BES *bonus*; Doc C consumes them.
- **LLM pre-clustering of raw findings into bug classes** — design B "Open items"; RESOLVE extraction here is council/single-agent judgment, not an automated clusterer.
- **Idempotency markers (`.extract_markers/`)** for extraction/promotion — noted as a design open item; not built (re-running RESOLVE extraction is acceptable because OKF ids are topic-named and writes are overwrites, not appends).
