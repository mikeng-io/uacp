"""Lesson & knowledge corpora — OKF dataclasses, BES scorer, recurrence math.

Pure, side-effect-free: ONLY the dataclasses, ``parse_okf``, the BES math, and
the in-memory ``*_for_project`` filters live here. No disk I/O — the disk corpus
loaders live in :mod:`engines.oracle.corpus_io` (inside the oracle package that
owns the corpus) and the writers in :mod:`engines.oracle.corpus_writer`, so the
corpus-ownership boundary is structural, not merely grep-enforced. Only the
explicit ``parse_okf`` / ``from_okf`` helpers raise.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    rest = text[len("---") :]
    end = rest.find("\n---")
    if end == -1:
        raise OKFParseError("OKF doc missing closing '---' frontmatter fence")
    fm_text = rest[:end]
    body = rest[end + len("\n---") :].lstrip("\n")
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
    def from_okf(cls, text: str) -> Lesson:
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
    def from_okf(cls, text: str) -> KnowledgeItem:
        fm, body = parse_okf(text)
        ktype = str(fm.get("type", "pattern"))
        if ktype not in KNOWLEDGE_TYPES:
            raise ValueError(f"knowledge type {ktype!r} must be one of {KNOWLEDGE_TYPES}")
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


def _parse_ts(value: str | int | float) -> datetime | None:
    # started_at is stored as an epoch int (run-registry schema); lesson.extracted_at
    # is an ISO string. Accept both so int-keyed runs are not silently dropped (#113).
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, tz=UTC)
        except (ValueError, OSError, OverflowError):
            return None
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
    updated = dataclasses.replace(
        lesson, eligible=eligible, recurrences=recurrences, bes=round(bes, 6)
    )
    return updated


PROMOTION_DEFAULTS = {
    "effective_bes_min": 0.85,  # "consistently effective" BES cutoff
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


def lessons_for_project(lessons: list[Lesson], project: str) -> list[Lesson]:
    """Lessons are project-local: keep only those tagged with ``project``."""
    return [lesson for lesson in lessons if lesson.project == project]


def knowledge_for_project(items: list[KnowledgeItem], project: str) -> list[KnowledgeItem]:
    """Knowledge query surface: this project's items plus shared items."""
    return [k for k in items if k.scope == project or k.scope == "shared"]
