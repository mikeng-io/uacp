"""Deterministic corpus retrieval FLOOR (#100) — no vector store, no ML deps.

When the semantic Oracle is off (``[oracle].enabled = false``) or its vector store is
unavailable (lancedb absent / index not built), retrieval must not collapse to empty:
a fact learned in run N must still surface in run N+50 on a fresh clone. This provides
a DETERMINISTIC keyword + domain + BES scan over the lesson/knowledge corpus, returning
advisory-trust ``ProviderPacket``s. Import-clean by construction: it depends only on the
Oracle floor (``corpus_writer`` readers, ``corpus`` dataclasses, ``packets``) — never on
lancedb/llama_cpp/httpx — so it runs on a bare clone.

Ranking (deterministic, explainable):
  * domain overlap with the requested domains (strong signal),
  * query-keyword overlap over title/body/invariants/tags,
  * lesson effectiveness (BES) as a tie-breaking weight.
When neither a domain filter nor a query is given, it surfaces the highest-BES lessons +
knowledge so the floor is never silent for a fresh run's TRIAGE.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from engines.oracle import corpus_writer
from engines.oracle.packets import ProviderPacket, TrustClass

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(*texts: str) -> set[str]:
    out: set[str] = set()
    for t in texts:
        out.update(w for w in _WORD_RE.findall(t.lower()) if len(w) > 2)
    return out


def _relevance(
    *, item_domains: list[str], text_tokens: set[str], want_domains: set[str], q_tokens: set[str]
) -> float:
    """A bounded [0,1] deterministic relevance from domain + keyword overlap."""
    score = 0.0
    if want_domains and (want_domains & {d.lower() for d in item_domains}):
        score += 0.6
    if q_tokens:
        overlap = len(q_tokens & text_tokens)
        score += min(overlap, 4) * 0.1  # up to +0.4
    return min(1.0, score)


def deterministic_corpus_packets(
    workspace: Path | str,
    project: str,
    *,
    domains: list[str] | None = None,
    query: str = "",
    limit: int = 20,
) -> list[ProviderPacket]:
    """Return advisory ProviderPackets from a deterministic scan of the lesson + knowledge
    corpus. Never raises (a broken corpus doc is skipped by the loaders); returns [] only
    when the corpus is genuinely empty."""
    want_domains = {d.lower() for d in (domains or [])}
    q_tokens = _tokens(query)
    no_filter = not want_domains and not q_tokens

    scored: list[tuple[float, float, str, Any]] = []  # (relevance, bes, kind, item)

    for lesson in corpus_writer.load_lessons(workspace):
        # Project scoping: a run for `project` sees its own lessons (+ project-less ones),
        # not another project's.
        if lesson.project and lesson.project != project:
            continue
        text_tokens = _tokens(
            lesson.title, lesson.body, " ".join(lesson.invariants), " ".join(lesson.tags)
        )
        rel = _relevance(
            item_domains=lesson.domains,
            text_tokens=text_tokens,
            want_domains=want_domains,
            q_tokens=q_tokens,
        )
        if rel > 0.0 or no_filter:
            scored.append((rel, float(lesson.bes), "lesson", lesson))

    for item in corpus_writer.load_knowledge(workspace):
        # Knowledge is "shared" or scoped to a project key; a run sees shared + its own.
        if item.scope not in ("shared", project):
            continue
        text_tokens = _tokens(item.title, item.body, item.description, " ".join(item.tags))
        rel = _relevance(
            item_domains=item.domains,
            text_tokens=text_tokens,
            want_domains=want_domains,
            q_tokens=q_tokens,
        )
        if rel > 0.0 or no_filter:
            scored.append((rel, 0.5, "knowledge", item))  # knowledge carries no BES

    # Rank by relevance, then BES (effectiveness) as the deterministic tie-break.
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)

    packets: list[ProviderPacket] = []
    for rel, bes, kind, item in scored[:limit]:
        # The floor SCORE blends relevance with effectiveness so a highly-effective lesson
        # ranks above a marginally-relevant one; when unfiltered (no_filter) relevance is 0
        # so BES alone orders the surfaced set.
        final = rel if not no_filter else round(bes, 3)
        packets.append(
            ProviderPacket(
                source="corpus-floor",
                trust_class=TrustClass.advisory,
                payload={
                    "kind": kind,
                    "id": item.id,
                    "title": item.title,
                    "body": item.body,
                    "domains": list(item.domains),
                },
                score=round(final, 3),
                metadata={"deterministic": True, "corpus": kind, "bes": round(bes, 3)},
            )
        )
    return packets
