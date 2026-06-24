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

from codeflair.crossplane import ManifestRef

# Identifier-shaped tokens, >=4 chars.
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_.]{3,}")
# Keep only tokens that look DELIBERATELY like code — a CamelCase hump, an underscore, a
# leading capital, or dotted member access — so prose words ("create", "the") are dropped
# while real mentions ("Execute", "CancelOrderUseCase", "cancel_order", "Pool.Conn") survive.
_CODEISH = re.compile(r"[a-z][A-Z]|_|^[A-Z]|[A-Za-z]\.[A-Za-z]")


def candidate_tokens(text: str) -> list[str]:
    """Deterministically extract code-identifier-shaped tokens from intent text, in order,
    de-duplicated case-insensitively."""
    out: list[str] = []
    seen: set[str] = set()
    for m in _IDENT.finditer(text or ""):
        tok = m.group(0).strip(".")
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
