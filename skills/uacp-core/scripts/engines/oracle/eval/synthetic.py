"""Deterministic synthetic OKF corpus generator for Oracle index/retrieval tests.

NO LLM, NO SDK, NO network. ``generate_corpus`` writes ``n`` valid OKF
lesson/knowledge markdown files (frontmatter that BOTH ``corpus_io`` loaders and
the OKF frontmatter lint accept) across several governance domains, each built
from a deterministic template with a DISTINCTIVE topic. It also returns a known
relevance map: ``(query, expected_top_item_id)`` pairs whose query is
SEMANTICALLY (paraphrased — not a substring) tied to exactly one item, so a
real embedding model must rank that item top via the dense leg, not via lexical
FTS overlap.

Determinism guarantee
---------------------
Pure function of ``(n, seed)``. Topic selection, file content, and the relevance
map are all derived from a fixed topic table indexed by a seeded permutation
(``random.Random(seed)``), with NO time/uuid/host inputs. The same ``(dest, n,
seed)`` therefore yields byte-identical files and an identical relevance map.
The frontmatter is emitted by hand (stable key order, no ``yaml.safe_dump`` set
ordering) to keep bytes reproducible across Python/yaml versions.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Topic table — each topic has a distinctive subject, a body that describes it,
# and a PARAPHRASED query that shares (ideally) no rare keyword with the body so
# a top rank is evidence of semantic (dense) retrieval, not lexical FTS overlap.
# Domains/invariants are drawn from the real UACP governance vocabulary.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Topic:
    slug: str
    title: str
    domain: str
    invariant: str
    severity: str
    # The descriptive body (what the item is "about").
    body: str
    # A semantically-equivalent paraphrase used as the retrieval query. It must
    # avoid reusing the body's most distinctive nouns to prove dense retrieval.
    query: str


_TOPICS: tuple[_Topic, ...] = (
    _Topic(
        slug="parallel-edit-isolation",
        title="Isolate parallel agent edits",
        domain="lifecycle",
        invariant="no-main-writes",
        severity="HIGH",
        body=(
            "When several autonomous workers modify the same files at once they "
            "overwrite one another. Give each worker its own isolated working "
            "copy so simultaneous changes never collide or clobber each other."
        ),
        query="how do concurrent agents avoid stepping on each other's changes",
    ),
    _Topic(
        slug="evidence-before-closure",
        title="Require evidence before closing work",
        domain="verify",
        invariant="evidence-required-closure",
        severity="CRITICAL",
        body=(
            "Declaring something finished without a backing artifact and a ledger "
            "record is forbidden. Completion must always be supported by proof "
            "that the work was actually carried out; no self-asserted sign-off."
        ),
        query="why can't a task be marked done just by saying so",
    ),
    _Topic(
        slug="council-not-a-store",
        title="The council deliberates, it does not persist",
        domain="council",
        invariant="council-gate",
        severity="MEDIUM",
        body=(
            "Strategy and design debate happens in the deliberation plane; that "
            "plane is not durable memory. Findings raised during review must be "
            "settled before the plan is allowed to advance past the review gate."
        ),
        query="should design discussion be used as a database for task state",
    ),
    _Topic(
        slug="phase-skip-blocks",
        title="Skipping a phase is a hard stop",
        domain="heartgate",
        invariant="triage-first",
        severity="HIGH",
        body=(
            "Every move between stages is checked. Jumping straight ahead without "
            "going through the earlier required step is rejected outright rather "
            "than merely flagged; the check fails shut, not open."
        ),
        query="what happens if you try to jump past a required stage transition",
    ),
    _Topic(
        slug="governed-writes-only",
        title="All mutations go through governed writers",
        domain="execute",
        invariant="governed-writers-only",
        severity="HIGH",
        body=(
            "Touching the filesystem directly during an active run is not allowed. "
            "Every persistent change must flow through an audited write surface so "
            "the boundary enforcer can inspect it before it lands on disk."
        ),
        query="can a running job write files straight to disk without auditing",
    ),
    _Topic(
        slug="degrade-to-floor",
        title="Retrieval degrades to the keyword floor",
        domain="oracle",
        invariant="evidence-required-floor",
        severity="LOW",
        body=(
            "When the vector model or its dependency is missing, the lookup does "
            "not fail. It falls back to a lightweight keyword-and-scoring path so "
            "results still come back, just without the dense semantic ranking."
        ),
        query="what does search do when the embedding model is not installed",
    ),
    _Topic(
        slug="lessons-carry-effectiveness",
        title="Lessons are weighted by past effectiveness",
        domain="resolve",
        invariant="evidence-required-recurrence",
        severity="MEDIUM",
        body=(
            "A recorded lesson keeps a running estimate of how useful it has been. "
            "Higher historical usefulness pushes it up the ranking, while advice "
            "that keeps failing to prevent repeats is pushed back down."
        ),
        query="how is prior-art advice ordered by how well it worked before",
    ),
    _Topic(
        slug="worktree-cleanup",
        title="Unused isolated copies are cleaned up",
        domain="lifecycle",
        invariant="no-main-writes-cleanup",
        severity="LOW",
        body=(
            "A throwaway working area that ends a run unchanged is removed "
            "automatically. Only copies that actually accumulated edits are kept "
            "around for the integration step afterwards."
        ),
        query="are untouched temporary working directories discarded after a run",
    ),
)

# Knowledge items use one of these OKF types (accepted by KnowledgeItem.from_okf
# AND the OKF lint). Lessons use type "lessons" (accepted by the lint; ignored by
# Lesson.from_okf). We avoid "digest" so we don't need a 'resource' field.
_KNOWLEDGE_TYPES = ("pattern", "analysis", "contract")


@dataclass
class CorpusItemSpec:
    id: str
    kind: str  # "lesson" | "knowledge"
    type: str
    domain: str
    invariant: str
    path: Path


@dataclass
class CorpusSpec:
    """What ``generate_corpus`` produced.

    Attributes:
        root: the dest directory (holds ``lessons/`` and ``knowledge/``).
        items: per-item specs (id, kind, type, domain, invariant, path).
        relevance: ``(query, expected_top_item_id)`` pairs, one per item that
            owns a distinctive topic; the query is a semantic paraphrase.
    """

    root: Path
    items: list[CorpusItemSpec] = field(default_factory=list)
    relevance: list[tuple[str, str]] = field(default_factory=list)


def _yaml_list(values: list[str]) -> str:
    """Inline YAML flow list with stable ordering (no set/dict reordering)."""
    return "[" + ", ".join(values) + "]"


def _lesson_doc(*, item_id: str, topic: _Topic, project: str) -> str:
    """A valid OKF lesson: passes Lesson.from_okf AND the OKF lint."""
    fm = (
        "---\n"
        "type: lessons\n"
        f"id: {item_id}\n"
        f"title: {topic.title}\n"
        f"description: {topic.body}\n"
        f"project: {project}\n"
        f"domains: {_yaml_list([topic.domain])}\n"
        f"invariants: {_yaml_list([topic.invariant])}\n"
        f"severity: {topic.severity}\n"
        "eligible: 6\n"
        "recurrences: 1\n"
        "bes: 0.9\n"
        "tags: " + _yaml_list([topic.domain, "synthetic"]) + "\n"
        "---\n"
    )
    return fm + f"\n# {topic.title}\n\n{topic.body}\n"


def _knowledge_doc(*, item_id: str, topic: _Topic, ktype: str) -> str:
    """A valid OKF knowledge item: passes KnowledgeItem.from_okf AND the OKF lint."""
    fm = (
        "---\n"
        f"type: {ktype}\n"
        f"id: {item_id}\n"
        f"title: {topic.title}\n"
        f"description: {topic.body}\n"
        f"domains: {_yaml_list([topic.domain])}\n"
        "scope: shared\n"
        "tags: " + _yaml_list([topic.domain, "synthetic"]) + "\n"
        "---\n"
    )
    return fm + f"\n# {topic.title}\n\n{topic.body}\n"


def generate_corpus(
    dest: Path,
    *,
    n: int,
    seed: int = 0,
    project: str = "synthetic",
) -> CorpusSpec:
    """Write ``n`` deterministic OKF items under ``dest`` and return a CorpusSpec.

    Items alternate lesson/knowledge and cycle through the distinctive topic
    table (with a topic-index suffix once topics repeat, so ids and content stay
    unique and the relevance map points at exactly one item per query). Fully
    deterministic in ``(n, seed)``: same inputs -> byte-identical files + map.

    Raises ValueError for ``n < 1``.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    dest = Path(dest)
    lessons_dir = dest / "lessons"
    knowledge_dir = dest / "knowledge"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    # Deterministic topic order from the seed (permutation of the topic table).
    order = list(range(len(_TOPICS)))
    rng.shuffle(order)

    spec = CorpusSpec(root=dest)
    seen_topics: set[int] = set()

    for i in range(n):
        topic_idx = order[i % len(_TOPICS)]
        topic = _TOPICS[topic_idx]
        # Distinct id even when topics repeat: append the global item index.
        item_id = f"{topic.slug}-{i:03d}"
        is_lesson = (i % 2) == 0

        if is_lesson:
            text = _lesson_doc(item_id=item_id, topic=topic, project=project)
            path = lessons_dir / f"{item_id}.md"
            item_type = "lessons"
            kind = "lesson"
        else:
            # Deterministic knowledge type from the seeded rng.
            ktype = _KNOWLEDGE_TYPES[rng.randrange(len(_KNOWLEDGE_TYPES))]
            text = _knowledge_doc(item_id=item_id, topic=topic, ktype=ktype)
            path = knowledge_dir / f"{item_id}.md"
            item_type = ktype
            kind = "knowledge"

        path.write_text(text, encoding="utf-8")
        spec.items.append(
            CorpusItemSpec(
                id=item_id,
                kind=kind,
                type=item_type,
                domain=topic.domain,
                invariant=topic.invariant,
                path=path,
            )
        )
        # Emit a relevance pair only for the FIRST item carrying each distinctive
        # topic, so every query maps to EXACTLY ONE expected id (no ambiguity
        # once topics repeat at n > len(_TOPICS)).
        if topic_idx not in seen_topics:
            seen_topics.add(topic_idx)
            spec.relevance.append((topic.query, item_id))

    return spec
