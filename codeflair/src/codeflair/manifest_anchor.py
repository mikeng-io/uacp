"""Bind UACP manifest intent to code — the INFERRED-anchor path (cross-plane v1).

Grounded finding (UACP, 2026-06-25): manifests today carry intent TEXT
(``work_unit.intent``, ``scope_item.statement``), not explicit code references —
``code_anchor``/``code_symbol`` appear nowhere in UACP yet (only in the design). So with
no ``code_refs`` field to read, v1 INFERS anchors: extract identifier-like tokens from the
intent text and resolve them against the code graph (the resolver filters to real symbols,
so over-extraction is harmless). Deterministic, no LLM.

The proper long-term path is an explicit ``code_refs`` field on manifest entities (a small
UACP schema addition); then this inference is unnecessary and anchors become authored, not
guessed.

UACP-AGNOSTIC (CF-D9): operates on plain projected manifest-node dicts
(``{id, kind, intent|statement}``) — the shim that reads
``engines/manifest/projection.py`` output and writes ``code_anchor`` back through the
governed entity writer is the only ``uacp`` import, and lives ABOVE this in UACP.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from codeflair.crossplane import AnchorResult, CrossPlaneAdapter, ManifestRef

# Identifier-shaped tokens, >=4 chars.
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.]{3,}")
# Keep only tokens that look DELIBERATELY like code — a CamelCase hump, an underscore, a
# leading capital, or dotted member access — so prose words ("create", "the") are dropped
# while real mentions ("Execute", "CancelOrderUseCase", "cancel_order", "Pool.Conn") survive.
_CODEISH = re.compile(r"[a-z][A-Z]|_|^[A-Z]|[A-Za-z]\.[A-Za-z]")
# File paths (cancel.go) look code-ish via the dot but are NOT symbol names — drop them so
# they don't show up as unresolved noise. (Member access like Pool.Conn is kept.)
_FILE_EXT = (
    ".go",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".rs",
    ".java",
    ".rb",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".txt",
    ".toml",
)


def candidate_tokens(text: str) -> list[str]:
    """Deterministically extract code-identifier-shaped tokens from intent text, in order,
    de-duplicated case-insensitively. File-path tokens are dropped (not symbol names)."""
    out: list[str] = []
    seen: set[str] = set()
    for m in _IDENT.finditer(text or ""):
        tok = m.group(0).strip(".")
        if tok.lower().endswith(_FILE_EXT):
            continue
        if len(tok) >= 4 and _CODEISH.search(tok) and tok.lower() not in seen:
            seen.add(tok.lower())
            out.append(tok)
    return out


def refs_from_manifest_nodes(
    nodes: list[dict],
    *,
    intent_keys: tuple[str, ...] = ("intent", "statement"),
    rel: str = "realizes",
) -> list[ManifestRef]:
    """Turn projected manifest nodes into candidate :class:`ManifestRef`s by mining their
    intent text. One ref per (node, distinct code-ish token); the adapter's resolver then
    keeps only those that hit a real symbol."""
    refs: list[ManifestRef] = []
    for node in nodes:
        nid = node.get("id")
        if not nid:
            continue
        kind = node.get("kind", "work_unit")
        text = " ".join(str(node.get(k, "")) for k in intent_keys if node.get(k))
        for tok in candidate_tokens(text):
            refs.append(ManifestRef(manifest_id=nid, kind=kind, code_ref=tok, rel=rel))
    return refs


@dataclass(frozen=True)
class RunAnchorReport:
    """The cross-plane summary for one run's manifest nodes — the read-only deliverable
    (Shim step A). Computes anchors into Codeflair's own ``code_anchor`` table and reports;
    it does NOT write anything into UACP's governed manifest graph (that is step B)."""

    anchored: list[AnchorResult]  # exactly one symbol matched — a clean anchor
    ambiguous: list[AnchorResult]  # >1 symbol matched — needs disambiguation
    unresolved: list[AnchorResult]  # 0 matched — intent referencing no real code
    orphan_code_count: int  # repo symbols no manifest node governs
    unrealized_manifest_ids: list[str]  # manifest nodes that anchored to no code


def anchor_run(adapter: CrossPlaneAdapter, nodes: list[dict]) -> RunAnchorReport:
    """Anchor a run's projected manifest ``nodes`` against the code graph and summarize.

    READ-ONLY w.r.t. UACP: it resolves + records anchors in Codeflair's own store and
    returns a report. Pushing these into UACP's governed graph (registering the
    ``code_anchor`` edge kind + the governed write) is the separate step B.
    """
    results = adapter.ingest(refs_from_manifest_nodes(nodes))
    by = {"anchored": [], "ambiguous": [], "unresolved": []}
    for r in results:
        by[r.status].append(r)
    manifest_ids = [n["id"] for n in nodes if n.get("id")]
    return RunAnchorReport(
        anchored=by["anchored"],
        ambiguous=by["ambiguous"],
        unresolved=by["unresolved"],
        orphan_code_count=len(adapter.orphan_code()),
        unrealized_manifest_ids=adapter.unrealized_manifests(manifest_ids),
    )
